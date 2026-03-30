/**
 * Google Sites Bridge — Apps Script Web App
 *
 * This script acts as a REST API bridge for creating pages on Google Sites.
 * Deploy as a web app to get a URL that distribute.py can POST to.
 *
 * SETUP:
 * 1. Go to https://script.google.com → New Project
 * 2. Paste this entire file into Code.gs
 * 3. Click Deploy → New deployment → Web app
 *    - Execute as: Me
 *    - Who has access: Anyone (or "Anyone with the link")
 * 4. Copy the Web App URL → paste into distribute config as google_sites.webapp_url
 * 5. Set a secret key below (shared between this script and distribute.py)
 *
 * GOOGLE SITES SETUP:
 * 1. Create a new Google Site at https://sites.google.com
 * 2. Get the Site ID from the URL: https://sites.google.com/d/SITE_ID/...
 *    Or from the published URL
 * 3. Set SITE_URL below to your published site URL
 */

// ─── Configuration ───────────────────────────────────────────────────────────

// Secret key for authentication (set the same value in distribute config)
var SECRET_KEY = PropertiesService.getScriptProperties().getProperty('SECRET_KEY') || 'CHANGE_ME';

// Your Google Sites published URL (for building page links)
var SITE_URL = PropertiesService.getScriptProperties().getProperty('SITE_URL') || 'https://sites.google.com/view/YOUR-SITE-NAME';


// ─── Web App Handlers ────────────────────────────────────────────────────────

/**
 * Handle GET requests — health check / list pages
 */
function doGet(e) {
  var params = e.parameter || {};

  if (params.action === 'health') {
    return jsonResponse({ status: 'ok', version: '1.0', site_url: SITE_URL });
  }

  if (params.action === 'list') {
    if (params.key !== SECRET_KEY) {
      return jsonResponse({ error: 'Invalid secret key' }, 403);
    }
    var pages = listPages();
    return jsonResponse({ pages: pages, count: pages.length });
  }

  return jsonResponse({
    status: 'Google Sites Bridge v1.0',
    endpoints: {
      'GET ?action=health': 'Health check',
      'GET ?action=list&key=SECRET': 'List all pages',
      'POST': 'Create a new page (JSON body with key, title, body, tags, canonical_url)'
    }
  });
}


/**
 * Handle POST requests — create a new page
 */
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
  } catch (err) {
    return jsonResponse({ error: 'Invalid JSON payload' }, 400);
  }

  // Auth check
  if (payload.key !== SECRET_KEY) {
    return jsonResponse({ error: 'Invalid secret key' }, 403);
  }

  var title = (payload.title || '').trim();
  var body = (payload.body || '').trim();
  var tags = payload.tags || [];
  var canonicalUrl = (payload.canonical_url || '').trim();
  var action = (payload.action || 'create').trim();

  if (!title) {
    return jsonResponse({ error: 'Title is required' }, 400);
  }
  if (!body) {
    return jsonResponse({ error: 'Body is required' }, 400);
  }

  if (action === 'create') {
    return createPage(title, body, tags, canonicalUrl);
  } else if (action === 'delete') {
    return deletePage(payload.page_id);
  }

  return jsonResponse({ error: 'Unknown action: ' + action }, 400);
}


// ─── Page Operations ─────────────────────────────────────────────────────────

/**
 * Create a page as a Google Doc and link it to Sites.
 *
 * Since Google Sites API (new) doesn't support programmatic page creation,
 * we create a Google Doc with the content and store the metadata in a spreadsheet
 * that serves as our "pages database". The Doc URL is the dofollow backlink.
 */
function createPage(title, body, tags, canonicalUrl) {
  try {
    // 1. Create a Google Doc with the article content
    var doc = DocumentApp.create(title);
    var docBody = doc.getBody();

    // Clear default empty paragraph
    docBody.clear();

    // Add title as heading
    var titleParagraph = docBody.appendParagraph(title);
    titleParagraph.setHeading(DocumentApp.ParagraphHeading.HEADING1);

    // Add tags line
    if (tags && tags.length > 0) {
      var tagsText = 'Tags: ' + tags.join(', ');
      var tagsPara = docBody.appendParagraph(tagsText);
      tagsPara.editAsText().setFontSize(10);
      tagsPara.editAsText().setItalic(true);
    }

    docBody.appendParagraph(''); // spacer

    // Parse markdown body into Doc elements
    var paragraphs = body.split('\n\n');
    for (var i = 0; i < paragraphs.length; i++) {
      var p = paragraphs[i].trim();
      if (!p) continue;

      // Headers
      if (p.indexOf('## ') === 0) {
        var h2 = docBody.appendParagraph(p.substring(3));
        h2.setHeading(DocumentApp.ParagraphHeading.HEADING2);
        continue;
      }
      if (p.indexOf('### ') === 0) {
        var h3 = docBody.appendParagraph(p.substring(4));
        h3.setHeading(DocumentApp.ParagraphHeading.HEADING3);
        continue;
      }
      if (p.indexOf('# ') === 0) {
        var h1 = docBody.appendParagraph(p.substring(2));
        h1.setHeading(DocumentApp.ParagraphHeading.HEADING1);
        continue;
      }

      // Horizontal rule
      if (p.match(/^---+$/)) {
        docBody.appendHorizontalRule();
        continue;
      }

      // Bullet lists
      if (p.indexOf('- ') === 0 || p.indexOf('* ') === 0) {
        var items = p.split('\n');
        for (var j = 0; j < items.length; j++) {
          var item = items[j].replace(/^[\-\*]\s+/, '').trim();
          if (item) {
            var li = docBody.appendListItem(item);
            li.setGlyphType(DocumentApp.GlyphType.BULLET);
          }
        }
        continue;
      }

      // Numbered lists
      if (p.match(/^\d+\.\s/)) {
        var numItems = p.split('\n');
        for (var k = 0; k < numItems.length; k++) {
          var numItem = numItems[k].replace(/^\d+\.\s+/, '').trim();
          if (numItem) {
            var numLi = docBody.appendListItem(numItem);
            numLi.setGlyphType(DocumentApp.GlyphType.NUMBER);
          }
        }
        continue;
      }

      // Regular paragraph — handle inline markdown links
      var para = docBody.appendParagraph('');
      appendRichText(para, p);
    }

    // Add canonical link at bottom
    if (canonicalUrl) {
      docBody.appendParagraph(''); // spacer
      docBody.appendHorizontalRule();
      var footerPara = docBody.appendParagraph('');
      footerPara.appendText('Originally published at ');
      footerPara.appendText(canonicalUrl).setLinkUrl(canonicalUrl);
    }

    doc.saveAndClose();

    // 2. Make the doc publicly viewable (this is the dofollow link!)
    var docFile = DriveApp.getFileById(doc.getId());
    docFile.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

    // 3. Move to a dedicated folder (organize)
    var folder = getOrCreateFolder('Teamz Lab Articles');
    docFile.moveTo(folder);

    // 4. Store metadata in our tracking spreadsheet
    var pageUrl = doc.getUrl();
    trackPage(doc.getId(), title, pageUrl, tags, canonicalUrl);

    return jsonResponse({
      status: 'created',
      url: pageUrl,
      doc_id: doc.getId(),
      title: title
    });

  } catch (err) {
    return jsonResponse({ error: 'Failed to create page: ' + err.message }, 500);
  }
}


/**
 * Delete a page by doc ID
 */
function deletePage(pageId) {
  if (!pageId) {
    return jsonResponse({ error: 'page_id is required' }, 400);
  }
  try {
    var file = DriveApp.getFileById(pageId);
    file.setTrashed(true);

    // Remove from tracker
    removePageFromTracker(pageId);

    return jsonResponse({ status: 'deleted', doc_id: pageId });
  } catch (err) {
    return jsonResponse({ error: 'Failed to delete: ' + err.message }, 500);
  }
}


/**
 * List all tracked pages
 */
function listPages() {
  var sheet = getTrackerSheet();
  if (!sheet) return [];

  var data = sheet.getDataRange().getValues();
  var pages = [];

  // Skip header row
  for (var i = 1; i < data.length; i++) {
    if (data[i][0]) {
      pages.push({
        doc_id: data[i][0],
        title: data[i][1],
        url: data[i][2],
        tags: data[i][3],
        canonical_url: data[i][4],
        created: data[i][5]
      });
    }
  }
  return pages;
}


// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Parse inline markdown (links, bold, italic) and append to paragraph
 */
function appendRichText(para, text) {
  // Process line by line for multi-line paragraphs
  var lines = text.split('\n');
  for (var li = 0; li < lines.length; li++) {
    if (li > 0) para.appendText('\n');
    var line = lines[li];

    // Pattern: [text](url), **bold**, *italic*
    var pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)]+)\))/g;
    var lastIndex = 0;
    var match;

    while ((match = pattern.exec(line)) !== null) {
      // Plain text before match
      if (match.index > lastIndex) {
        para.appendText(line.substring(lastIndex, match.index));
      }

      if (match[2]) {
        // Bold: **text**
        para.appendText(match[2]).setBold(true);
      } else if (match[3]) {
        // Italic: *text*
        para.appendText(match[3]).setItalic(true);
      } else if (match[4] && match[5]) {
        // Link: [text](url)
        para.appendText(match[4]).setLinkUrl(match[5]);
      }

      lastIndex = match.index + match[0].length;
    }

    // Remaining text
    if (lastIndex < line.length) {
      para.appendText(line.substring(lastIndex));
    }
  }
}


/**
 * Get or create a Drive folder for articles
 */
function getOrCreateFolder(name) {
  var folders = DriveApp.getFoldersByName(name);
  if (folders.hasNext()) {
    return folders.next();
  }
  return DriveApp.createFolder(name);
}


/**
 * Get or create the tracker spreadsheet
 */
function getTrackerSheet() {
  var files = DriveApp.getFilesByName('Teamz Lab Articles Tracker');
  if (files.hasNext()) {
    return SpreadsheetApp.open(files.next()).getActiveSheet();
  }
  return null;
}


function getOrCreateTrackerSheet() {
  var sheet = getTrackerSheet();
  if (sheet) return sheet;

  var ss = SpreadsheetApp.create('Teamz Lab Articles Tracker');
  sheet = ss.getActiveSheet();
  sheet.appendRow(['doc_id', 'title', 'url', 'tags', 'canonical_url', 'created']);

  // Move to articles folder
  var folder = getOrCreateFolder('Teamz Lab Articles');
  DriveApp.getFileById(ss.getId()).moveTo(folder);

  return sheet;
}


/**
 * Track a page in the spreadsheet
 */
function trackPage(docId, title, url, tags, canonicalUrl) {
  var sheet = getOrCreateTrackerSheet();
  sheet.appendRow([
    docId,
    title,
    url,
    (tags || []).join(', '),
    canonicalUrl || '',
    new Date().toISOString()
  ]);
}


/**
 * Remove a page from the tracker
 */
function removePageFromTracker(docId) {
  var sheet = getTrackerSheet();
  if (!sheet) return;

  var data = sheet.getDataRange().getValues();
  for (var i = data.length - 1; i >= 0; i--) {
    if (data[i][0] === docId) {
      sheet.deleteRow(i + 1);
      return;
    }
  }
}


/**
 * Return a JSON response
 */
function jsonResponse(data, code) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}


// ─── Setup Helper ────────────────────────────────────────────────────────────

/**
 * Run this once to set your secret key and site URL.
 * Go to: Project Settings → Script Properties, OR run this function manually.
 */
function setupProperties() {
  var ui = SpreadsheetApp.getUi();

  // Set via Script Properties (recommended)
  PropertiesService.getScriptProperties().setProperties({
    'SECRET_KEY': 'YOUR_SECRET_KEY_HERE',
    'SITE_URL': 'https://sites.google.com/view/YOUR-SITE-NAME'
  });

  Logger.log('Properties set! Deploy as web app to get the URL.');
  Logger.log('SECRET_KEY and SITE_URL are stored in Script Properties.');
}
