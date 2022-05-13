package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;

import javax.swing.Box;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JPanel;

import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;

class FlagPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final LabeledComboBox _flag_box;

	public FlagPanel() {
		_flag_box = new LabeledComboBox();
		_flag_box.setLabel("set_flag");
		_flag_box.setModel(new DefaultComboBoxModel(Entry.Stats.UserFlag
				.values()));

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		add(_flag_box.getLabel(), cc);
		cc.update(2, 0, 0.0, 0.0);
		add(_flag_box, cc);
	}

	public Entry.Stats.UserFlag getSelectedItem() {
		return (Entry.Stats.UserFlag) _flag_box.getSelectedItem();
	}

	public void setSelectedItem(Entry.Stats.UserFlag flag) {
		_flag_box.setSelectedItem(flag);
	}
}
