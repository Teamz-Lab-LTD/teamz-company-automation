#!/usr/bin/env ruby
# Generic achievement sync — Apple Game Center + Google Play Games.
#
# Reads a project-local spec file and creates / updates achievements
# on both stores. Used by per-app fastlane lanes; safe to invoke
# directly from CLI for ad-hoc syncs.
#
# Usage:
#   ruby sync_game_achievements.rb \
#       --spec=<path/to/star-achievements.json> \
#       --platform=both|apple|google \
#       --apply             # without --apply, runs in DRY mode
#       --writeback=<path>  # path to a Dart file with playGames/gameCenter
#                            id maps to update with generated IDs
#
# Required env (loaded from .teamz-automation.env or .appstore-fastlane.env):
#   ASC_KEY_ID
#   ASC_ISSUER_ID
#   ASC_KEY_FILEPATH         (e.g. ~/.config/teamzlab/AuthKey_xxx.p8)
#   PLAY_SERVICE_ACCOUNT_JSON (e.g. ~/.config/teamzlab/play-console-service-account.json)
#
# Exit codes:
#   0 = success
#   1 = config error
#   2 = partial failure (some platforms / achievements failed)

require 'json'
require 'net/http'
require 'uri'
require 'time'
require 'optparse'
require 'openssl'
require 'base64'
require 'fileutils'

# ──────────────────────────────────────────────────────────────────
# CLI args
# ──────────────────────────────────────────────────────────────────
options = {
  spec: nil,
  platform: 'both',
  apply: false,
  writeback: nil
}
OptionParser.new do |opts|
  opts.banner = 'Usage: sync_game_achievements.rb [options]'
  opts.on('--spec=PATH') { |v| options[:spec] = v }
  opts.on('--platform=NAME', %w[both apple google]) { |v| options[:platform] = v }
  opts.on('--apply') { options[:apply] = true }
  opts.on('--writeback=PATH') { |v| options[:writeback] = v }
end.parse!

abort('--spec=<path> required') if options[:spec].nil?
abort("spec file not found: #{options[:spec]}") unless File.exist?(options[:spec])

SPEC = JSON.parse(File.read(options[:spec]))
DRY = !options[:apply]

def env_or(name, fallback = nil)
  v = ENV[name] || ENV["TEAMZ_#{name}"]
  return v if v && !v.empty?
  fallback
end

def expand(p)
  return nil if p.nil?
  File.expand_path(p)
end

ASC_KEY_ID    = env_or('ASC_KEY_ID')
ASC_ISSUER_ID = env_or('ASC_ISSUER_ID')
ASC_KEY_PATH  = expand(env_or('ASC_KEY_FILEPATH'))
PLAY_SA_PATH  = expand(env_or('PLAY_SERVICE_ACCOUNT_JSON'))

def section(t)
  puts ''
  puts '━' * 64
  puts t
  puts '━' * 64
end

def log(level, msg)
  prefix = case level
           when :ok then '✓'
           when :warn then '⚠'
           when :err then '❌'
           when :dry then '·'
           else '  '
           end
  puts "#{prefix} #{msg}"
end

# ──────────────────────────────────────────────────────────────────
# Apple — Game Center sync via direct ASC REST
# ──────────────────────────────────────────────────────────────────
def asc_jwt
  pkey = OpenSSL::PKey::EC.new(File.read(ASC_KEY_PATH))
  header = { alg: 'ES256', kid: ASC_KEY_ID, typ: 'JWT' }
  now = Time.now.to_i
  claims = {
    iss: ASC_ISSUER_ID, iat: now, exp: now + 1200, aud: 'appstoreconnect-v1'
  }
  enc = ->(o) { Base64.urlsafe_encode64(JSON.generate(o), padding: false) }
  unsigned = "#{enc.call(header)}.#{enc.call(claims)}"
  raw = pkey.sign(OpenSSL::Digest::SHA256.new, unsigned)
  asn = OpenSSL::ASN1.decode(raw)
  r = asn.value[0].value.to_s(2).rjust(32, "\0")
  s = asn.value[1].value.to_s(2).rjust(32, "\0")
  "#{unsigned}.#{Base64.urlsafe_encode64(r + s, padding: false)}"
end

def asc_request(method, path, jwt, body = nil)
  uri = URI("https://api.appstoreconnect.apple.com#{path}")
  klass = case method
          when :get then Net::HTTP::Get
          when :post then Net::HTTP::Post
          when :patch then Net::HTTP::Patch
          when :delete then Net::HTTP::Delete
          end
  req = klass.new(uri)
  req['Authorization'] = "Bearer #{jwt}"
  req['Content-Type'] = 'application/json'
  req.body = JSON.generate(body) if body
  resp = Net::HTTP.start(uri.host, uri.port, use_ssl: true) { |h| h.request(req) }
  [resp.code.to_i, (resp.body && !resp.body.empty? ? (JSON.parse(resp.body) rescue resp.body) : nil)]
end

def apple_sync
  section('APPLE — Game Center sync')
  return log(:err, 'ASC_KEY_FILEPATH missing or unreadable') unless ASC_KEY_PATH && File.exist?(ASC_KEY_PATH)

  jwt = asc_jwt
  apple_cfg = SPEC['apple']
  app_id = apple_cfg['app_id']

  status, detail = asc_request(:get, "/v1/apps/#{app_id}/gameCenterDetail", jwt)
  unless status == 200 && detail&.dig('data', 'id')
    return log(:err, "gameCenterDetail not found (#{status}). Enable Game Center in ASC for app #{app_id}.")
  end
  detail_id = detail['data']['id']
  log(:ok, "Game Center detail #{detail_id}")

  # Fetch existing achievements (paginate up to 200)
  status, list = asc_request(:get, "/v1/gameCenterDetails/#{detail_id}/gameCenterAchievements?limit=200", jwt)
  existing = (list && list['data']) || []
  by_vendor = {}
  existing.each do |a|
    vid = a.dig('attributes', 'vendorIdentifier')
    by_vendor[vid] = a if vid
  end
  log(:ok, "#{existing.size} existing Game Center achievement(s)")

  results = { created: [], updated: [], failed: [] }

  SPEC['achievements'].each do |spec|
    vendor = spec['vendor_id']
    found = by_vendor[vendor]
    if found
      # Patch attributes if drifted
      attrs = found['attributes'] || {}
      desired = {
        referenceName: spec['reference_name'],
        points: spec['points'],
        showBeforeEarned: spec['show_before_earned'] != false,
        repeatable: spec['repeatable'] == true
      }
      drift = desired.any? { |k, v| attrs[k.to_s] != v }
      if drift
        if DRY
          log(:dry, "[apple] would PATCH #{vendor}: #{desired.inspect}")
          results[:updated] << vendor
        else
          patch_body = {
            data: {
              type: 'gameCenterAchievements',
              id: found['id'],
              attributes: desired
            }
          }
          ps, _ = asc_request(:patch, "/v1/gameCenterAchievements/#{found['id']}", jwt, patch_body)
          if ps == 200
            log(:ok, "[apple] updated #{vendor}")
            results[:updated] << vendor
          else
            log(:err, "[apple] update failed #{vendor} (#{ps})")
            results[:failed] << vendor
          end
        end
      else
        log(:ok, "[apple] up-to-date #{vendor}")
      end
    else
      body = {
        data: {
          type: 'gameCenterAchievements',
          attributes: {
            referenceName: spec['reference_name'],
            vendorIdentifier: vendor,
            points: spec['points'],
            showBeforeEarned: spec['show_before_earned'] != false,
            repeatable: spec['repeatable'] == true
          },
          relationships: {
            gameCenterDetail: {
              data: { type: 'gameCenterDetails', id: detail_id }
            }
          }
        }
      }
      if DRY
        log(:dry, "[apple] would CREATE #{vendor}")
        results[:created] << vendor
      else
        cs, cb = asc_request(:post, '/v1/gameCenterAchievements', jwt, body)
        if cs == 201
          ach_id = cb.dig('data', 'id')
          log(:ok, "[apple] created #{vendor} (id=#{ach_id})")
          results[:created] << vendor
          # Localization (en-US, primary): create localization with title + before/after descriptions
          loc_body = {
            data: {
              type: 'gameCenterAchievementLocalizations',
              attributes: {
                locale: SPEC['primary_locale'] || 'en-US',
                name: spec['title'],
                beforeEarnedDescription: spec['description_pre'],
                afterEarnedDescription: spec['description_post']
              },
              relationships: {
                gameCenterAchievement: {
                  data: { type: 'gameCenterAchievements', id: ach_id }
                }
              }
            }
          }
          ls, _ = asc_request(:post, '/v1/gameCenterAchievementLocalizations', jwt, loc_body)
          if ls == 201
            log(:ok, "[apple] localized #{vendor} (#{SPEC['primary_locale']})")
          else
            log(:warn, "[apple] localization failed #{vendor} (#{ls})")
          end
        else
          log(:err, "[apple] create failed #{vendor} (#{cs}): #{cb}")
          results[:failed] << vendor
        end
      end
    end
  end

  results
end

# ──────────────────────────────────────────────────────────────────
# Google — Play Games sync via gamesconfiguration API
# ──────────────────────────────────────────────────────────────────
def google_oauth_token
  sa = JSON.parse(File.read(PLAY_SA_PATH))
  header = { alg: 'RS256', typ: 'JWT' }
  now = Time.now.to_i
  claims = {
    iss: sa['client_email'],
    scope: 'https://www.googleapis.com/auth/androidpublisher',
    aud: 'https://oauth2.googleapis.com/token',
    exp: now + 3600,
    iat: now
  }
  enc = ->(o) { Base64.urlsafe_encode64(JSON.generate(o), padding: false) }
  unsigned = "#{enc.call(header)}.#{enc.call(claims)}"
  pkey = OpenSSL::PKey::RSA.new(sa['private_key'])
  sig = Base64.urlsafe_encode64(pkey.sign(OpenSSL::Digest::SHA256.new, unsigned), padding: false)
  jwt = "#{unsigned}.#{sig}"

  resp = Net::HTTP.post_form(
    URI('https://oauth2.googleapis.com/token'),
    'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'assertion' => jwt
  )
  raise "oauth #{resp.code}: #{resp.body[0, 300]}" unless resp.is_a?(Net::HTTPSuccess)
  JSON.parse(resp.body)['access_token']
end

def gpg_request(method, url, token, body = nil)
  uri = URI(url)
  klass = case method
          when :get then Net::HTTP::Get
          when :post then Net::HTTP::Post
          when :put then Net::HTTP::Put
          when :patch then Net::HTTP::Patch
          end
  req = klass.new(uri)
  req['Authorization'] = "Bearer #{token}"
  req['Content-Type'] = 'application/json'
  req.body = JSON.generate(body) if body
  resp = Net::HTTP.start(uri.host, uri.port, use_ssl: true) { |h| h.request(req) }
  [resp.code.to_i, (resp.body && !resp.body.empty? ? (JSON.parse(resp.body) rescue resp.body) : nil)]
end

def google_sync
  section('GOOGLE — Play Games Services sync')
  return log(:err, 'PLAY_SERVICE_ACCOUNT_JSON missing') unless PLAY_SA_PATH && File.exist?(PLAY_SA_PATH)

  token = google_oauth_token
  log(:ok, "OAuth token minted")

  app_id = SPEC.dig('google', 'application_id')
  unless app_id
    log(:err, 'spec.google.application_id missing')
    return { failed: SPEC['achievements'].map { |a| a['local_id'] } }
  end

  list_url = "https://gamesconfiguration.googleapis.com/games/v1configuration/applications/#{app_id}/achievements"
  status, body = gpg_request(:get, list_url, token)
  unless status == 200
    log(:err, "list failed #{status}: #{body.inspect[0, 400]}")
    if status == 403
      sa = JSON.parse(File.read(PLAY_SA_PATH))
      log(:warn, "Enable: https://console.developers.google.com/apis/api/gamesconfiguration.googleapis.com/overview")
      log(:warn, "Add as PGS Project member: #{sa['client_email']}")
    end
    return { failed: SPEC['achievements'].map { |a| a['local_id'] } }
  end

  existing = body['items'] || []
  # Play Games has no client-provided unique key — match existing
  # achievements by the en-US draft name (the visible title). Two
  # achievements with the same title would collide; spec titles are
  # already unique so this is safe.
  primary_locale = SPEC['primary_locale'] || 'en-US'
  by_title = {}
  existing.each do |a|
    title = (a.dig('draft', 'name', 'translations') || [])
              .find { |t| t['locale'] == primary_locale }&.dig('value')
    by_title[title] = a if title
  end

  log(:ok, "#{existing.size} existing Play Games achievement(s)")

  results = { created: [], updated: [], failed: [] }
  generated_ids = {}

  SPEC['achievements'].each do |spec|
    title = spec['title']
    found = by_title[title]
    if found
      results[:updated] << title
      generated_ids[spec['local_id']] = found['id']
      log(:ok, "[google] exists '#{title}' → id=#{found['id']}")
      next
    end

    payload = {
      kind: 'gamesConfiguration#achievementConfiguration',
      achievementType: spec['steps_to_unlock'].to_i > 1 ? 'INCREMENTAL' : 'STANDARD',
      initialState: spec['hidden'] ? 'HIDDEN' : 'REVEALED',
      draft: {
        kind: 'gamesConfiguration#achievementConfigurationDetail',
        name: {
          kind: 'gamesConfiguration#localizedStringBundle',
          translations: [{
            kind: 'gamesConfiguration#localizedString',
            locale: primary_locale,
            value: title
          }]
        },
        description: {
          kind: 'gamesConfiguration#localizedStringBundle',
          translations: [{
            kind: 'gamesConfiguration#localizedString',
            locale: primary_locale,
            value: spec['description_pre']
          }]
        },
        pointValue: spec['points'].to_i,
        sortOrder: 0
      }
    }
    payload[:stepsToUnlock] = spec['steps_to_unlock'].to_i if spec['steps_to_unlock'].to_i > 1

    if DRY
      log(:dry, "[google] would CREATE '#{title}'")
      results[:created] << title
    else
      cs, cb = gpg_request(:post, list_url, token, payload)
      if cs == 200 || cs == 201
        ach_id = cb['id']
        log(:ok, "[google] created '#{title}' → id=#{ach_id}")
        results[:created] << title
        generated_ids[spec['local_id']] = ach_id
      else
        log(:err, "[google] create failed '#{title}' (#{cs}): #{cb.inspect[0, 600]}")
        results[:failed] << title
      end
    end
  end

  results.merge(generated_ids: generated_ids)
end

# ──────────────────────────────────────────────────────────────────
# Writeback — patch generated Play Games IDs into app_config.dart
# ──────────────────────────────────────────────────────────────────
def writeback(path, generated_ids)
  return if generated_ids.nil? || generated_ids.empty?
  unless File.exist?(path)
    log(:warn, "writeback: #{path} missing")
    return
  end
  src = File.read(path)
  changed = false
  # Sort by length DESC so longer placeholders replace before shorter
  # ones — prevents `TODO_..._streak_3` from clobbering the prefix of
  # `TODO_..._streak_30`.
  generated_ids.sort_by { |k, _| -k.length }.each do |local_id, real_id|
    placeholder = "TODO_PLAY_GAMES_ID_#{local_id}"
    if src.include?(placeholder)
      src = src.gsub(placeholder, real_id)
      changed = true
      log(:ok, "writeback: #{local_id} → #{real_id}")
    end
  end
  if changed
    if DRY
      log(:dry, "writeback: would update #{path}")
    else
      File.write(path, src)
      log(:ok, "writeback: wrote #{path}")
    end
  end
end

# ──────────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────────
puts ''
puts "Spec: #{options[:spec]}"
puts "Mode: #{DRY ? 'DRY-RUN (--apply to commit)' : 'APPLY'}"
puts "Platforms: #{options[:platform]}"

apple_results = nil
google_results = nil

if %w[apple both].include?(options[:platform])
  apple_results = apple_sync
end
if %w[google both].include?(options[:platform])
  google_results = google_sync
end

if options[:writeback] && google_results && google_results[:generated_ids]
  section('WRITEBACK')
  writeback(options[:writeback], google_results[:generated_ids])
end

section('SUMMARY')
[%w[apple Apple], %w[google Google]].each do |k, label|
  r = (k == 'apple' ? apple_results : google_results)
  next unless r
  puts "#{label}: created=#{r[:created]&.size || 0} updated=#{r[:updated]&.size || 0} failed=#{r[:failed]&.size || 0}"
end

failed_total = (apple_results&.dig(:failed)&.size || 0) + (google_results&.dig(:failed)&.size || 0)
exit(failed_total > 0 ? 2 : 0)
