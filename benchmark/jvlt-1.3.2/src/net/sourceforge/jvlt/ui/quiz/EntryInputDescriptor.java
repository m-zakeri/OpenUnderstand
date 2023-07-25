package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Vector;

import javax.swing.JCheckBox;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.vocabulary.EntryInfoPanel;
import net.sourceforge.jvlt.utils.I18nService;

class EntryInputDescriptor extends EntryDescriptor implements ActionListener,
		ChangeListener {
	private CustomTextField _input_field;
	private JCheckBox _box;
	private JLabel _lbl;
	private int _questions = 0;

	public EntryInputDescriptor(QuizModel m, SelectionNotifier n) {
		super(m, n);
		
		_info_panel.setMode(EntryInfoPanel.Mode.QUIZ);
	}

	@Override
	public String getID() {
		return "entry_input";
	}

	public boolean isAnswerKnown() {
		return _box.isSelected();
	}

	public int getNumberOfQuestions() {
		return _questions;
	}

	public String[] getAnswer() {
		String answers_delimiter = JVLT.getConfig().getProperty(
				"answers_delimiter", ",");
		String text = _input_field.getText();
		if (text.length() == 0) {
			return new String[0];
		}

		String[] answer;
		if (_questions == 1) {
			answer = new String[] { text };
		} else {
			answer = text.split(answers_delimiter);
		}

		// Strip leading and trailing blank spaces
		for (int i = 0; i < answer.length; i++) {
			answer[i] = answer[i].replaceAll("^\\s+", "");
			answer[i] = answer[i].replaceAll("\\s+$", "");
		}

		return answer;
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("answer_known")) {
			_input_field.setEnabled(_box.isSelected());
			_model.panelDescriptorUpdated();
		}
	}

	public void stateChanged(ChangeEvent ev) {
		_model.panelDescriptorUpdated();
	}

	@Override
	public void prepareToShow() {
		_input_field.setText("");
		_input_field.setEnabled(true);
		_input_field.requestFocusInWindow();
		_box.setSelected(true);
	}

	@Override
	protected void init() {
		_lbl = new JLabel();
		_input_field = new CustomTextField(20);
		_input_field.addChangeListener(this);
		_box = new JCheckBox(GUIUtils.createTextAction(this, "answer_known"));
		JPanel input_panel = new JPanel();
		input_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		input_panel.add(_lbl, cc);
		cc.update(1, 0, 0.0, 0.0);
		input_panel.add(_box, cc);
		cc.update(2, 0, 0.0, 0.0);
		input_panel.add(_input_field, cc);

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 1.0);
		_panel.add(_info_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(input_panel, cc);
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

			Entry entry = getEntry();
			String quizzed_attrs[] = _quiz_info.getQuizzedAttributes();

			// Only attributes with value will be included.
			Vector<String> quizzed_present_attrs = new Vector<String>();
			QuizModel model = (QuizModel) _model;
			for (String quizzedAttr : quizzed_attrs) {
				Attribute attr = model.getJVLTModel().getDictModel()
						.getMetaData(Entry.class).getAttribute(quizzedAttr);
				if (attr.getValue(entry) != null) {
					quizzed_present_attrs.add(quizzedAttr);
				}
			}
			_questions = quizzed_present_attrs.size();

			String attr = formatAttributeList(quizzed_present_attrs
					.toArray(new String[0]));
			String labelText = I18nService.getString("Messages",
					"entry_known_question", new Object[] { attr });

			if (quizzed_present_attrs.size() > 1) {
				String answers_delimiter = JVLT.getConfig().getProperty(
						"answers_delimiter", ",");
				labelText += " "
						+ I18nService.getString("Messages",
								"use_answers_delimiter",
								new Object[] { answers_delimiter });
			}
			_lbl.setText(labelText);
		}
	}
}
