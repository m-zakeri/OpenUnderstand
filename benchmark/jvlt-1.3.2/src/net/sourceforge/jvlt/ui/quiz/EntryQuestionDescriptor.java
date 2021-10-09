package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;

import javax.swing.JLabel;
import javax.swing.JPanel;

import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.vocabulary.EntryInfoPanel;
import net.sourceforge.jvlt.utils.I18nService;

class EntryQuestionDescriptor extends EntryDescriptor {
	private JLabel _lbl;

	public EntryQuestionDescriptor(QuizModel m, SelectionNotifier n) {
		super(m, n);
		
		_info_panel.setMode(EntryInfoPanel.Mode.QUIZ);
	}

	@Override
	public String getID() {
		return "entry_question";
	}

	@Override
	protected void init() {
		_lbl = new JLabel();

		JPanel p = new JPanel();
		p.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		p.add(_info_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		p.add(_lbl, cc);

		_panel = p;
	}

	@Override
	protected void entryAttributesUpdated() {
		if (_quiz_info == null) {
			_info_panel.setDisplayedEntryAttributes(new String[0]);
			_info_panel.setDisplayedExampleAttributes(new String[0]);
		} else {
			String[] attrs = _quiz_info.getShownAttributes();
			_info_panel.setDisplayedEntryAttributes(attrs);
			_info_panel.setDisplayedExampleAttributes(new String[0]);

			String quizzed_attrs[] = _quiz_info.getQuizzedAttributes();
			String attr = formatAttributeList(quizzed_attrs);
			if (attr != null && !attr.equals("")) {
				_lbl.setText(I18nService.getString("Messages",
						"entry_known_question", new Object[] { attr }));
			}
		}
	}
}
