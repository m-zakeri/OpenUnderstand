<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns:xslutils="net.sourceforge.jvlt.ui.utils.XSLUtils">

<xsl:output method="html" indent="yes"/>

<xsl:template match="dictionary">
	<html>
	<head>
	<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1"/>
	</head>
	<body>
	<h3>
	<xsl:value-of select="xslutils:i18nString('original')"/>
	<xsl:text> &#8658; </xsl:text>
	<xsl:value-of select="xslutils:i18nString('translation')"/>
	</h3>
	<xsl:apply-templates select="entry"/>
	<br/>
	<xsl:apply-templates select="reverse"/>
	</body>
	</html>
</xsl:template>

<xsl:template match="entry">
	<p>
	<xsl:apply-templates select="multimedia"/>
	<b><xsl:value-of select="orth"/></b>
	<xsl:text> </xsl:text>
	<xsl:if test="count(pron) > 0">
		[<xsl:apply-templates select="pron"/>]
		<xsl:text> </xsl:text>
	</xsl:if>
	<xsl:call-template name="process-attributes">
		<xsl:with-param name="entry-id" select="@id"/>
	</xsl:call-template>
	<xsl:apply-templates select="sense"/>
	</p>
	<div style="clear: both;"/>
</xsl:template>

<xsl:template match="multimedia">
	<xsl:if test="xslutils:mimeType(.) = 'image'">
		<img>
		<xsl:attribute name="src">
			<xsl:value-of select="xslutils:filePath(.)"/>
		</xsl:attribute>
		<xsl:attribute name="style">float: left;</xsl:attribute>
		</img>
	</xsl:if>
</xsl:template>

<xsl:template match="pron">
	<xsl:if test="position() > 1">
		<xsl:text>, </xsl:text>
	</xsl:if>
	<xsl:value-of select="."/>
</xsl:template>

<xsl:template name="process-attributes">
	<xsl:param name="entry-id"/>
	<xsl:variable name="entry" select="/dictionary/entry[@id=$entry-id]"/>
	
	<xsl:if test="$entry/@class">
		<i>
		<xsl:text>(</xsl:text>
		<xsl:value-of select="xslutils:translate($entry/@class)"/>
		<xsl:apply-templates select="attr"/>
		<xsl:text>) </xsl:text>
		</i>
	</xsl:if>
</xsl:template>

<xsl:template match="attr">
	<xsl:text>; </xsl:text>
	<xsl:value-of select="xslutils:translate(@name)"/>
	<xsl:text>: </xsl:text>
	<xsl:value-of select="xslutils:translate(.)"/>
</xsl:template>

<xsl:template match="sense">
	<xsl:if test="count(../sense)>1">
		<xsl:value-of select="position()"/>.
		<xsl:text> </xsl:text>
	</xsl:if>
	<xsl:if test="string(def)">
		<i>(<xsl:value-of select="def"/>)</i>
		<xsl:text> </xsl:text>
	</xsl:if>
	<xsl:if test="string(trans)">
		<xsl:value-of select="trans"/>
		<xsl:text> </xsl:text>
	</xsl:if>
	<xsl:text> </xsl:text>
	<xsl:call-template name="process-examples">
		<xsl:with-param name="sense-id" select="@id"/>
	</xsl:call-template>
</xsl:template>

<xsl:template name="process-examples">
	<xsl:param name="sense-id"/>

	<xsl:for-each select="/dictionary/example[ex/link/@sid=$sense-id]">
		<xsl:if test="position() > 1">
			<!-- HTML &diams; entity -->
			<xsl:text>&#9830;</xsl:text>
		</xsl:if>
		<i>
		<span style="font-size:small;">
		<xsl:apply-templates select="ex/*|ex/text()">
			<xsl:with-param name="sense-id" select="$sense-id"/>
		</xsl:apply-templates>
		<xsl:if test="string(tr)">
			- <xsl:value-of select="tr"/>
		</xsl:if>
		</span>
		</i>
		<xsl:text> </xsl:text>
	</xsl:for-each>
</xsl:template>

<xsl:template match="link">
	<xsl:param name="sense-id"/>
	<xsl:choose>
		<xsl:when test="@sid=$sense-id">
			<b><xsl:value-of select="."/></b>
		</xsl:when>
		<xsl:otherwise>
			<xsl:value-of select="."/>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>

<xsl:template match="reverse">
	<h3>
	<xsl:value-of select="xslutils:i18nString('translation')"/>
	<xsl:text> &#8658; </xsl:text>
	<xsl:value-of select="xslutils:i18nString('original')"/>
	</h3>
	<xsl:apply-templates select="sense-ref"/>
</xsl:template>

<xsl:template match="sense-ref">
	<!-- variables -->
	<xsl:variable name="sense-id" select="@sense-id"/>
	<xsl:variable name="entry-id" select="@entry-id"/>
	<xsl:variable name="entry"
		select="/dictionary/entry[@id = $entry-id]"/>
	<xsl:variable name="sense"
		select="/dictionary/entry/sense[@id = $sense-id]"/>
	
	<p>
	<xsl:if test="string($sense/trans)">
		<b><xsl:value-of select="$sense/trans"/></b>
		<xsl:text> </xsl:text>
		<xsl:value-of select="$entry/orth"/>
	</xsl:if>
	<xsl:text> </xsl:text>
	<xsl:call-template name="process-examples">
		<xsl:with-param name="sense-id" select="$sense-id"/>
	</xsl:call-template>
	</p>
</xsl:template>

</xsl:stylesheet>

