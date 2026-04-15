#!/usr/bin/env ruby
# Pulls monthly SALES/SUMMARY reports from App Store Connect, aggregates,
# and writes a CSV. Monthly frequency is used because ASC only retains
# dailies for ~30 days — monthly is the only option that reaches "lifetime".

require 'net/http'
require 'uri'
require 'zlib'
require 'stringio'
require 'csv'
require 'date'
require 'fileutils'

$LOAD_PATH.unshift(File.expand_path('../lib', __dir__))
require 'asc_jwt'

RANGE = ARGV[0] || 'lifetime'
OUT_DIR = ARGV[1] or abort('usage: ios_sales.rb <range> <out_dir>')
FileUtils.mkdir_p(OUT_DIR)

%w[ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_FILEPATH ASC_VENDOR_NUMBER].each do |k|
  abort("missing env: #{k}") if ENV[k].nil? || ENV[k].empty?
end

def range_months(range)
  today = Date.today
  case range
  when 'last-30d' then [today.prev_month.strftime('%Y-%m')]
  when 'last-90d' then (0..2).map { |i| today.prev_month(i).strftime('%Y-%m') }.reverse
  when 'ytd'      then (1..today.month - 1).map { |m| format('%04d-%02d', today.year, m) }
  else # lifetime — ASC rejects dates before app's first sale with 404; we walk from 2015 and swallow 404s.
    start = Date.new(2015, 1, 1)
    months = []
    cursor = start
    while cursor < Date.new(today.year, today.month, 1)
      months << cursor.strftime('%Y-%m')
      cursor = cursor.next_month
    end
    months
  end
end

def fetch_report(token, vendor, month)
  uri = URI('https://api.appstoreconnect.apple.com/v1/salesReports')
  uri.query = URI.encode_www_form(
    'filter[frequency]'     => 'MONTHLY',
    'filter[reportType]'    => 'SALES',
    'filter[reportSubType]' => 'SUMMARY',
    'filter[vendorNumber]'  => vendor,
    'filter[reportDate]'    => month
  )
  req = Net::HTTP::Get.new(uri)
  req['Authorization'] = "Bearer #{token}"
  req['Accept'] = 'application/a-gzip'

  res = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) { |h| h.request(req) }
  case res.code
  when '200'
    Zlib::GzipReader.new(StringIO.new(res.body)).read
  when '404', '410'
    nil
  else
    raise "ASC #{res.code}: #{res.body[0, 200]}"
  end
end

bundle_id = ENV['APP_BUNDLE_ID']
token = AscJwt.token(
  key_id: ENV['ASC_KEY_ID'],
  issuer_id: ENV['ASC_ISSUER_ID'],
  key_filepath: ENV['ASC_KEY_FILEPATH']
)

out_path = File.join(OUT_DIR, 'ios_sales.csv')
CSV.open(out_path, 'w') do |out|
  out << %w[month units proceeds_usd country sku]

  range_months(RANGE).each do |month|
    tsv = fetch_report(token, ENV['ASC_VENDOR_NUMBER'], month)
    next if tsv.nil?

    CSV.parse(tsv, col_sep: "\t", headers: true).each do |row|
      sku = row['SKU'] || row['Apple Identifier'] || ''
      next if bundle_id && !bundle_id.empty? && !sku.to_s.include?(bundle_id) && row['SKU'] != bundle_id
      out << [
        month,
        row['Units'] || row['Quantity'] || '0',
        row['Developer Proceeds'] || row['Royalty Price'] || '0',
        row['Country Code'] || '',
        sku
      ]
    end
  end
end

puts "wrote #{out_path}"
