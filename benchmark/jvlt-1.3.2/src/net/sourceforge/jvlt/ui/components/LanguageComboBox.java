package net.sourceforge.jvlt.ui.components;

import java.io.InputStream;
import java.util.HashMap;

import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;

import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.I18nService;

import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public class LanguageComboBox extends LabeledComboBox {
	private static final long serialVersionUID = 1L;

	private final HashMap<String, String> _language_map;

	public LanguageComboBox() {
		super();

		_language_map = new HashMap<String, String>();

		setLabel("language");
		addItem(I18nService.getString("Labels", "other_language"));
		try {
			InputStream is = LanguageComboBox.class
					.getResourceAsStream("/xml/info.xml");
			InputSource src = new InputSource(is);
			XPathFactory fac = XPathFactory.newInstance();
			XPath xpath = fac.newXPath();
			NodeList lang_nodes = (NodeList) xpath.evaluate("/info/language",
					src, XPathConstants.NODESET);
			AttributeResources ar = new AttributeResources();
			for (int i = 0; i < lang_nodes.getLength(); i++) {
				Element elem = (Element) lang_nodes.item(i);
				String name = elem.getAttribute("name");
				String translation = ar.getString(name);
				_language_map.put(translation, name);
				addItem(translation);
			}
		} catch (XPathExpressionException ex) {
			ex.printStackTrace();
		}
	}

	public String getSelectedLanguage() {
		Object lang = _language_map.get(getSelectedItem());
		return lang == null ? null : lang.toString();
	}

	public void setSelectedLanguage(String language) {
		if (language == null || language.equals("")) {
			setSelectedIndex(0);
		} else {
			AttributeResources resources = new AttributeResources();
			setSelectedItem(resources.getString(language));
		}
	}
}
