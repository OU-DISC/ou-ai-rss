<?xml version="1.0" encoding="UTF-8"?>
<!-- Makes the feed readable when opened directly in a browser. RSS readers ignore this. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8"/>
  <xsl:template match="/rss/channel">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title><xsl:value-of select="title"/></title>
        <style>
          body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:760px;margin:2rem auto;padding:0 16px;color:#222;background:#fff}
          .note{background:#f6eeee;border-left:4px solid #841617;padding:.8em 1em;margin:1em 0 2em}
          code{background:#eee;padding:.1em .35em;border-radius:3px;word-break:break-all}
          h1{color:#841617;font-size:1.6rem}
          .item{padding:1em 0;border-bottom:1px solid #ddd}
          .item a{color:#841617;font-weight:600;font-size:1.05rem;text-decoration:none}
          .meta{font-size:.85em;color:#666;margin:.2em 0}
        </style>
      </head>
      <body>
        <h1><xsl:value-of select="title"/></h1>
        <p><xsl:value-of select="description"/></p>
        <div class="note">This is an RSS feed. Copy this page's URL into your RSS reader (Feedly, Inoreader, Outlook, Thunderbird, etc.) to subscribe.</div>
        <xsl:for-each select="item">
          <div class="item">
            <a href="{link}"><xsl:value-of select="title"/></a>
            <div class="meta"><xsl:value-of select="category"/> · <xsl:value-of select="pubDate"/></div>
          </div>
        </xsl:for-each>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
