package net.sourceforge.jvlt.ui.dialogs;

import java.awt.GridBagLayout;

import javax.swing.Box;
import javax.swing.JPanel;

import net.sourceforge.jvlt.ui.components.LanguageComboBox;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.I18nService;

public class PropertiesDialogData extends CustomDialogData {
	private String _language;
	private final LanguageComboBox _language_box;

	public PropertiesDialogData(String language) {
		_language = language;

		_language_box = new LanguageComboBox();
		_language_box.setSelectedLanguage(_language);

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		_content_pane.add(_language_box.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		_content_pane.add(_language_box, cc);
		cc.update(0, 1, 0.0, 1.0);
		_content_pane.add(Box.createVerticalGlue(), cc);
	}

	public String getLanguage() {
		return _language;
	}

	@Override
	public void updateData() {
		String lang = _language_box.getSelectedLanguage();
		if (_language != null && !_language.equals("")
				&& (lang == null || !lang.equals(_language))) {
			int result = MessageDialog.showDialog(_content_pane,
					MessageDialog.WARNING_MESSAGE,
					MessageDialog.OK_CANCEL_OPTION, I18nService.getString(
							"Messages", "language_change"));
			if (result == MessageDialog.OK_OPTION) {
				_language = lang;
			}
		} else {
			_language = lang;
		}
	}
}
