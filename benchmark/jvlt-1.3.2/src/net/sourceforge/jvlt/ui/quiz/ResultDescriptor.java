package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Arrays;
import java.util.Map;

import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.wizard.WizardModel;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.I18nService;

class ResultDescriptor extends YesNoDescriptor implements
		ListSelectionListener, ActionListener {
	private CustomAction _up_action;
	private CustomAction _down_action;
	private ResultEntryTable _known_entries_table;
	private ResultEntryTable _notknown_entries_table;
	private JPanel _comp;
	private TitledBorder _known_entries_border;
	private TitledBorder _notknown_entries_border;

	public ResultDescriptor(WizardModel model) {
		super(model, I18nService.getString("Messages", "save_changes"));
		init();
		updateActions();
		updateLabels();
	}

	@Override
	public String getID() {
		return "result";
	}

	public Entry[] getKnownEntries() {
		return _known_entries_table.getEntries().toArray(new Entry[0]);
	}

	public void setKnownEntries(Entry[] entries) {
		_known_entries_table.setEntries(Arrays.asList(entries));
		updateLabels();
	}

	public Entry[] getNotKnownEntries() {
		return _notknown_entries_table.getEntries().toArray(new Entry[0]);
	}

	public void setNotKnownEntries(Entry[] entries) {
		_notknown_entries_table.setEntries(Arrays.asList(entries));
		updateLabels();
	}
	
	public Map<Entry, Integer> getFlagMap() {
		Map<Entry, Integer> flag_map = _known_entries_table.getFlagMap();
		flag_map.putAll(_notknown_entries_table.getFlagMap());
		
		return flag_map;
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting())
			updateActions();
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("up")) {
			Entry entry = _notknown_entries_table.getSelectedEntry();
			if (entry != null) {
				_notknown_entries_table.removeEntry(entry);
				_known_entries_table.addEntry(entry);
				updateLabels();
			}
		} else if (ev.getActionCommand().equals("down")) {
			Entry entry = _known_entries_table.getSelectedEntry();
			if (entry != null) {
				_known_entries_table.removeEntry(entry);
				_notknown_entries_table.addEntry(entry);
				updateLabels();
			}
		}
	}

	private void init() {
		_up_action = GUIUtils.createIconAction(this, "up");
		_down_action = GUIUtils.createIconAction(this, "down");

		_known_entries_table = new ResultEntryTable();
		_known_entries_table.getSelectionModel().addListSelectionListener(this);
		_known_entries_border = new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED));
		JScrollPane known_entries_scrpane = new JScrollPane();
		known_entries_scrpane.getViewport().setView(_known_entries_table);
		known_entries_scrpane.setBorder(_known_entries_border);
		_notknown_entries_table = new ResultEntryTable();
		_notknown_entries_table.getSelectionModel().addListSelectionListener(
				this);
		_notknown_entries_border = new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED));
		JScrollPane notknown_entries_scrpane = new JScrollPane();
		notknown_entries_scrpane.getViewport().setView(_notknown_entries_table);
		notknown_entries_scrpane.setBorder(_notknown_entries_border);

		JPanel up_down_panel = new JPanel();
		up_down_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		up_down_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		up_down_panel.add(new JButton(_down_action), cc);
		cc.update(2, 0);
		up_down_panel.add(new JButton(_up_action), cc);

		_comp = new JPanel();
		_comp.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 1.0);
		_comp.add(known_entries_scrpane, cc);
		cc.update(0, 1, 1.0, 0.0);
		_comp.add(up_down_panel, cc);
		cc.update(0, 2, 1.0, 1.0);
		_comp.add(notknown_entries_scrpane, cc);

		setContentPanel(_comp);
	}

	private void updateActions() {
		_down_action
				.setEnabled(_known_entries_table.getSelectedEntry() != null);
		_up_action
				.setEnabled(_notknown_entries_table.getSelectedEntry() != null);
	}

	private void updateLabels() {
		ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
				"Labels", "num_words"));
		String value = formatter
				.format(_known_entries_table.getEntries().size());
		_known_entries_border.setTitle(I18nService.getString("Labels",
				"known_words", new Object[] { value }));
		value = formatter.format(_notknown_entries_table.getEntries().size());
		_notknown_entries_border.setTitle(I18nService.getString("Labels",
				"not_known_words", new Object[] { value }));
		_comp.revalidate();
		_comp.repaint(_comp.getVisibleRect());
	}
}
