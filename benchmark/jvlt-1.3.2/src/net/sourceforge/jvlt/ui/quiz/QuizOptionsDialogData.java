package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.Box;
import javax.swing.JCheckBox;
import javax.swing.JPanel;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.dialogs.CustomDialogData;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.Config;
import net.sourceforge.jvlt.utils.I18nService;

public class QuizOptionsDialogData extends CustomDialogData {
	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("input_answer")) {
				boolean input_answer = _input_answer_chbox.isSelected();
				_match_case_chbox.setEnabled(input_answer);
				_default_answer_chbox.setEnabled(!input_answer);
				_default_answer_cobox.setEnabled(!input_answer
						&& _default_answer_chbox.isSelected());
			} else if (ev.getActionCommand().equals("default_answer")) {
				_default_answer_cobox.setEnabled(_default_answer_chbox
						.isSelected());
			} else if (ev.getActionCommand().equals("ignore_batches")) {
				_update_batches_chbox.setEnabled(_ignore_batches_chbox
						.isSelected());
			}
		}
	}

	private final boolean _old_input_answer;
	private final boolean _old_match_case;
	private final String _old_default_answer;
	private final boolean _old_ignore_batches;
	private final boolean _old_update_batches;
	private final boolean _old_play_audio;

	private JCheckBox _input_answer_chbox;
	private JCheckBox _match_case_chbox;
	private JCheckBox _default_answer_chbox;
	private LabeledComboBox _default_answer_cobox;
	private JCheckBox _ignore_batches_chbox;
	private JCheckBox _update_batches_chbox;
	private JCheckBox _play_audio_chbox;

	public QuizOptionsDialogData() {
		Config config = JVLT.getConfig();

		_old_input_answer = config.getBooleanProperty("input_answer", false);
		_old_match_case = config.getBooleanProperty("match_case", true);
		_old_default_answer = config.getProperty("default_answer", "");
		_old_ignore_batches = config
				.getBooleanProperty("ignore_batches", false);
		_old_update_batches = config
				.getBooleanProperty("update_batches", false);
		_old_play_audio = config.getBooleanProperty("Quiz.PlayAudio", false);

		initUi();
	}

	@Override
	public void updateData() {
		Config config = JVLT.getConfig();

		boolean new_input_answer = _input_answer_chbox.isSelected();
		boolean new_match_case = !_match_case_chbox.isSelected();
		String new_default_answer = "";
		if (_default_answer_chbox.isSelected()) {
			String item = _default_answer_cobox.getSelectedItem().toString();
			if (item.equals(I18nService.getString("Labels", "yes"))) {
				new_default_answer = "yes";
			} else {
				new_default_answer = "no";
			}
		}
		boolean new_ignore_batches = _ignore_batches_chbox.isSelected();
		boolean new_update_batches = _update_batches_chbox.isSelected();
		boolean new_play_audio = _play_audio_chbox.isSelected();

		config.setProperty("input_answer", new_input_answer);
		config.setProperty("match_case", new_match_case);
		config.setProperty("default_answer", new_default_answer);
		config.setProperty("ignore_batches", new_ignore_batches);
		config.setProperty("update_batches", new_update_batches);
		config.setProperty("Quiz.PlayAudio", new_play_audio);
	}

	private void initUi() {
		ActionHandler handler = new ActionHandler();
		CustomConstraints cc = new CustomConstraints();

		_input_answer_chbox = new JCheckBox(GUIUtils.createTextAction(handler,
				"input_answer"));
		_match_case_chbox = new JCheckBox(GUIUtils.createTextAction(handler,
				"ignore_case"));
		_default_answer_chbox = new JCheckBox(GUIUtils.createTextAction(
				handler, "default_answer"));
		_default_answer_cobox = new LabeledComboBox();
		_default_answer_cobox.setLabel("default_answer_choice");
		_default_answer_cobox.addItem(I18nService.getString("Labels", "yes"));
		_default_answer_cobox.addItem(I18nService.getString("Labels", "no"));
		_ignore_batches_chbox = new JCheckBox(GUIUtils.createTextAction(
				handler, "ignore_batches"));
		_update_batches_chbox = new JCheckBox(GUIUtils.createTextAction(
				handler, "update_batches"));
		_play_audio_chbox = new JCheckBox(GUIUtils.createTextAction(handler,
				"play_audio_during_quiz"));

		JPanel general_panel = new JPanel();
		general_panel.setLayout(new GridBagLayout());
		JPanel default_answer_panel = new JPanel();
		default_answer_panel.setLayout(new GridLayout());
		default_answer_panel.add(_default_answer_cobox.getLabel());
		default_answer_panel.add(_default_answer_cobox);
		cc.update(0, 0, 1.0, 0.0);
		general_panel.add(_input_answer_chbox, cc);
		cc.update(0, 1, 1.0, 0.0);
		cc.insets.left = 15;
		general_panel.add(_match_case_chbox, cc);
		cc.update(0, 2, 1.0, 0.0);
		general_panel.add(_default_answer_chbox, cc);
		cc.update(0, 3, 1.0, 0.0);
		cc.insets.left = 2;
		general_panel.add(default_answer_panel, cc);
		cc.update(0, 4, 1.0, 0.0);
		general_panel.add(_ignore_batches_chbox, cc);
		cc.update(0, 5, 1.0, 0.0);
		cc.insets.left = 15;
		general_panel.add(_update_batches_chbox, cc);
		cc.update(0, 6, 1.0, 0.0);
		cc.insets.left = 0;
		general_panel.add(_play_audio_chbox, cc);
		cc.update(0, 7, 1.0, 1.0);
		general_panel.add(Box.createVerticalGlue(), cc);

		_content_pane = general_panel;

		/*
		 * Initialize data
		 */
		_input_answer_chbox.setSelected(_old_input_answer);
		_match_case_chbox.setEnabled(_old_input_answer);
		_match_case_chbox.setSelected(!_old_match_case);
		_default_answer_chbox.setEnabled(!_old_input_answer);
		_default_answer_chbox.setSelected(!_old_default_answer.equals(""));
		_default_answer_cobox.setEnabled(!_old_input_answer
				&& !_old_default_answer.equals(""));
		_default_answer_cobox
				.setSelectedItem(_old_default_answer.equals("no") ? I18nService
						.getString("Labels", "no") : I18nService.getString(
						"Labels", "yes"));
		_ignore_batches_chbox.setSelected(_old_ignore_batches);
		_update_batches_chbox.setEnabled(_old_ignore_batches);
		_update_batches_chbox.setSelected(_old_update_batches);
		_play_audio_chbox.setSelected(_old_play_audio);
	}
}
