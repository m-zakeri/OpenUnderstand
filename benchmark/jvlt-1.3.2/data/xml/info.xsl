<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:xslutils="net.sourceforge.jvlt.ui.utils.XSLUtils">

	<xsl:template match="info">
		<html>
		<body style="xslutils:fontStyle('html_font')">
		<div align="center">
		<img src="jvlt.png" alt="jVLT logo" width="128" height="128"/>
		</div>
		<h1 align="center">
		<xsl:value-of select="name"/>
		</h1>
		<p align="center">
		<xsl:value-of select="xslutils:i18nString('version')"/>:
		<xsl:value-of select="version"/>
		</p>
		<h2 align="center">Developers</h2>
		<xsl:apply-templates select="developers/person"/>
		<h2 align="center">Translators</h2>
		<xsl:apply-templates select="translators/person"/>
		<h2 align="center">Contributors</h2>
		<xsl:apply-templates select="contributors/person"/>
		</body>
		</html>
	</xsl:template>

	<xsl:template match="person">
		<p align="center">
		<xsl:value-of select="name"/>
		<xsl:text> (</xsl:text>
			<xsl:value-of select="role"/>
		<xsl:text>)</xsl:text>
		<br/>
		<xsl:value-of select="e-mail/local-part"/>
		<xsl:text>@</xsl:text>
		<xsl:value-of select="e-mail/domain"/>
		</p>
		<br/>
	</xsl:template>
</xsl:stylesheet>

