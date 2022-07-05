package net.sourceforge.jvlt.ui.dialogs;

import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.ButtonGroup;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JRadioButton;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

public class ResetStatsDialogData extends CustomDialogData {
	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			updateLabelText();
		}
	}

	private int _num_entries = 0;
	private int _num_matched_entries = 0;

	private final JLabel _message_label;
	private final JRadioButton _all_entries_button;
	private final JRadioButton _displayed_entries_button;

	public ResetStatsDialogData(int num_entries, int num_matched_entries) {
		_num_entries = num_entries;
		_num_matched_entries = num_matched_entries;

		_message_label = new JLabel();

		ActionHandler handler = new ActionHandler();
		_all_entries_button = new JRadioButton(GUIUtils.createTextAction(
				handler, "all_entries"));
		_all_entries_button.setSelected(true);
		_displayed_entries_button = new JRadioButton(GUIUtils.createTextAction(
				handler, "vocabulary_list_words"));
		ButtonGroup group = new ButtonGroup();
		group.add(_all_entries_button);
		group.add(_displayed_entries_button);

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1, 1);
		_content_pane.add(_message_label, cc);
		cc.update(0, 1, 1, 0);
		_content_pane.add(_all_entries_button, cc);
		cc.update(0, 2, 1, 0);
		_content_pane.add(_displayed_entries_button, cc);

		updateLabelText();
	}

	@Override
	public void updateData() {
	}

	public boolean resetAllEntries() {
		return _all_entries_button.isSelected();
	}

	private void updateLabelText() {
		int num_cleaned_entries;
		if (_all_entries_button.isSelected()) {
			num_cleaned_entries = _num_entries;
		} else {
			num_cleaned_entries = _num_matched_entries;
		}

		_message_label
				.setText(I18nService.getString("Messages",
						"stats_deletion_warning",
						new Object[] { num_cleaned_entries }));
	}
}
