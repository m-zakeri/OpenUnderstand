<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:xslutils="net.sourceforge.jvlt.ui.utils.XSLUtils">

	<xsl:variable name="orth_font_style_family"
		select="xslutils:fontStyleFamily('orth_font')"/>
	<xsl:variable name="pron_font_style_family"
		select="xslutils:fontStyleFamily('pron_font')"/>
	<xsl:variable name="default_font_style"
		select="xslutils:fontStyle('html_font')"/>

	<xsl:template match="Dict">
		<html>
		
		<head>
		<link href="style.css" rel="stylesheet" type="text/css"/>
		</head>

		<body style="{$default_font_style}">
		
		<div class="hbar"/>
		<table width="100%" class="box1">
		<tr>
		<td valign="top">
		<table cellpadding="0" cellspacing="0">
		<tr>
		<td>
		<xsl:apply-templates select="Example/HTMLText/child::node()"/>
		</td>
		<xsl:if test="string(Example/Translation)">
			<td valign="center" class="vbar"/>
			<td>
			<xsl:apply-templates select="Example/Translation/child::node()"/>
			</td>
		</xsl:if>
		</tr>
		</table>
		</td>
		</tr>
		</table>
		<div class="hbar"/>

		<div style="margin-top:5pt;">
		<xsl:for-each select="Example/HTMLText//a">
			<xsl:call-template name="process-link">
				<xsl:with-param name="link" select="current()"/>
			</xsl:call-template>
		</xsl:for-each>
		</div>
		
		</body>
		</html>
	</xsl:template>

	<xsl:template name="process-link">
		<xsl:param name="link"/>
		<xsl:variable name="sid" select="$link/@href"/>
		<xsl:variable name="entry" select="/Dict/Entry[Senses/Sense/ID=$sid]"/>
		<div style="margin-top:2pt;">
		<a href="{$sid}" class="link">
		<font style="{$orth_font_style_family}">
		<xsl:value-of disable-output-escaping="yes"
			select="$entry/Orthography"/>
		</font>
		</a>
		<xsl:if test="$entry/Pronunciations/item">
			<font style="{$pron_font_style_family}">
			[<xsl:call-template name="process-item-list">
				<xsl:with-param name="item-list"
					select="$entry/Pronunciations/item"/>
			</xsl:call-template>]
			</font>
		</xsl:if>
		- <xsl:apply-templates select="$entry/Senses/Sense[ID=$sid]"/>
		</div>
	</xsl:template>

	<xsl:template match="Sense">
		<xsl:if test="string(Definition)">
			<i>(<xsl:value-of disable-output-escaping="yes"
				select="Definition"/>)</i>
			<xsl:if test="string(Translation)">, </xsl:if>
		</xsl:if>
		<xsl:value-of disable-output-escaping="yes" select="Translation"/>
	</xsl:template>

	<xsl:template name="process-item-list">
		<xsl:param name="item-list"/>
		<xsl:for-each select="$item-list">
			<xsl:if test="position()>1">, </xsl:if>
			<xsl:value-of disable-output-escaping="yes" select="."/>
		</xsl:for-each>
	</xsl:template>
	
	<xsl:template match="a">
		<a href="{@href}" class="link">
		<xsl:value-of disable-output-escaping="yes" select="."/>
		</a>
	</xsl:template>

	<xsl:template match="*">
		<xsl:element name="{name(.)}">
			<xsl:apply-templates/>
		</xsl:element>
	</xsl:template>

	<xsl:template match="text()">
		<xsl:value-of disable-output-escaping="yes" select="."/>
	</xsl:template>

</xsl:stylesheet>

