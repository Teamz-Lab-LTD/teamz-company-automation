#!/usr/bin/env ruby
# Direct App Store Connect screenshot uploader using Spaceship.
# Bypasses fastlane deliver to avoid silent-failure race conditions.
require 'spaceship'
require 'dotenv'
require 'digest'

Dotenv.load(File.expand_path('../.appstore-fastlane.env', __dir__))

KEY_ID = ENV['ASC_KEY_ID']
ISSUER_ID = ENV['ASC_ISSUER_ID']
P8_PATH = File.expand_path("~/.config/teamzlab/AuthKey_#{KEY_ID}.p8")
BUNDLE_ID = ENV['APP_BUNDLE_ID']
TARGET_VERSION = ENV.fetch('TARGET_VERSION', '2.1.0')
SS_ROOT = File.expand_path('../fastlane/screenshots', __dir__)

# Map fastlane folder name → ASC display type
DEVICE_MAP = {
  'APP_IPHONE_55'         => 'APP_IPHONE_55',
  'APP_IPHONE_65'         => 'APP_IPHONE_65',
  'APP_IPHONE_67'         => 'APP_IPHONE_67',
  'APP_IPAD_PRO_129'      => 'APP_IPAD_PRO_129',
  'APP_IPAD_PRO_3GEN_129' => 'APP_IPAD_PRO_3GEN_129',
}

# Auth
Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
  key_id: KEY_ID, issuer_id: ISSUER_ID, filepath: P8_PATH
)

app = Spaceship::ConnectAPI::App.find(BUNDLE_ID)
puts "App: #{app.name}"
version = app.get_app_store_versions.find { |v| v.version_string == TARGET_VERSION }
abort "Version #{TARGET_VERSION} not found" unless version
puts "Version: #{version.version_string} (#{version.app_store_state})"

# Push en-US screenshots to ALL 39 localizations (Apple doesn't auto-
# inherit across locales; empty locale slots fall back to the previous
# app version's screenshots, showing stale content).
locales_target = ENV.fetch('LOCALES', 'ALL')
locs = version.get_app_store_version_localizations
if locales_target != 'ALL'
  wanted = locales_target.split(',').map(&:strip)
  locs = locs.select { |l| wanted.include?(l.locale) }
end
puts "Target localizations: #{locs.size}"

total_uploaded = 0
locs.each_with_index do |loc, li|
  puts "\n\n### [#{li + 1}/#{locs.size}] #{loc.locale} ###"
  existing = loc.get_app_screenshot_sets
  if existing.any?
    puts "  Wiping #{existing.size} existing set(s)"
    existing.each do |s|
      begin
        s.app_screenshots.each(&:delete!)
        s.delete!
      rescue => e
        puts "  (skip wipe: #{e.message[0..80]})"
      end
    end
  end

  DEVICE_MAP.each do |folder, display_type|
    src_dir = File.join(SS_ROOT, 'en-US', folder)
    next unless Dir.exist?(src_dir)
    files = Dir[File.join(src_dir, '*.jpg')].sort
    next if files.empty?

    begin
      set = loc.create_app_screenshot_set(attributes: { screenshotDisplayType: display_type })
    rescue => e
      puts "  ✗ #{display_type} create: #{e.message[0..120]}"
      next
    end

    files.each_with_index do |f, idx|
      begin
        set.upload_screenshot(path: f, wait_for_processing: true)
        total_uploaded += 1
        print "."
      rescue => e
        print "✗"
        STDERR.puts "\n  #{loc.locale}/#{display_type}/#{File.basename(f)}: #{e.message[0..150]}"
      end
    end
    print " "
  end
  puts "  done (#{loc.locale})"
end

puts "\n#{'=' * 60}"
puts "Total screenshots uploaded across #{locs.size} locales: #{total_uploaded}"
puts "#{'=' * 60}"
