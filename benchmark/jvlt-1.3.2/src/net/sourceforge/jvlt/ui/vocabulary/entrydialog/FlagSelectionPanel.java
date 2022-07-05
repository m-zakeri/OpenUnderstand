package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.GridBagLayout;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.swing.Box;
import javax.swing.JCheckBox;
import javax.swing.JPanel;

import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;

class FlagSelectionPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final List<Entry> _entries;
	private final Map<JCheckBox, Entry.Stats.UserFlag> _flag_map;

	public FlagSelectionPanel(List<Entry> entries) {
		_entries = entries;
		_flag_map = new HashMap<JCheckBox, Entry.Stats.UserFlag>();

		setLayout(new GridBagLayout());

		init();
	}

	public void apply() {
		int flags = 0;

		for (JCheckBox cb : _flag_map.keySet()) {
			if (cb.isSelected()) {
				flags |= _flag_map.get(cb).getValue();
			}
		}

		for (Entry e : _entries) {
			e.setUserFlags(flags);
		}
	}

	private void init() {
		int shared_flags = 0;

		/*
		 * Determine the flags common for all entries
		 */
		for (Entry.Stats.UserFlag f : Entry.Stats.UserFlag.values()) {
			shared_flags |= f.getValue();
		}

		for (Entry e : _entries) {
			shared_flags &= e.getUserFlags();
		}

		/*
		 * Initialize check boxes
		 */
		int i = 0;
		CustomConstraints cc = new CustomConstraints();
		for (Entry.Stats.UserFlag f : Entry.Stats.UserFlag.values()) {
			if (f.getValue() == 0) {
				continue;
			}

			JCheckBox cb = new JCheckBox(f.toString());
			_flag_map.put(cb, f);

			/* Enable the check box only if all entries share the flag */
			cb.setSelected((shared_flags & f.getValue()) != 0);

			cc.update(0, i++, 1.0, 0.0);
			add(cb, cc);
		}

		cc.update(0, i, 0.0, 1.0);
		add(Box.createVerticalGlue(), cc);
	}
}
