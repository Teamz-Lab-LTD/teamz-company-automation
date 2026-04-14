# Shared JWT signer for App Store Connect API.
# ASC requires ES256 with a short-lived token (max 20 min per Apple docs).

require 'jwt'
require 'openssl'
require 'time'

module AscJwt
  AUDIENCE = 'appstoreconnect-v1'.freeze
  TTL_SECONDS = 1200

  def self.token(key_id:, issuer_id:, key_filepath:)
    path = File.expand_path(key_filepath)
    raise "ASC key file not found: #{path}" unless File.exist?(path)

    private_key = OpenSSL::PKey::EC.new(File.read(path))
    now = Time.now.to_i

    JWT.encode(
      {
        iss: issuer_id,
        iat: now,
        exp: now + TTL_SECONDS,
        aud: AUDIENCE
      },
      private_key,
      'ES256',
      { kid: key_id, typ: 'JWT' }
    )
  end
end
