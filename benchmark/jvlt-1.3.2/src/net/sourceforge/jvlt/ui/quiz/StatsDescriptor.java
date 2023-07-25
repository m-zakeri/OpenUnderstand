package net.sourceforge.jvlt.ui.quiz;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Collection;
import java.util.GregorianCalendar;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JEditorPane;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DictUpdateListener.DictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.EntryDictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.LanguageDictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.NewDictDictUpdateEvent;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.query.EntryFilter;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.quiz.QuizDict;
import net.sourceforge.jvlt.quiz.QuizInfo;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.CustomDialog;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.vocabulary.EntrySelectionDialogData;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.DefaultComparator;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;

class StatsDescriptor extends WizardPanelDescriptor implements ActionListener {
	private final Map<String, QuizInfo> _quiz_info_map;
	private final Map<String, QuizInfo> _visible_quiz_info_map;
	private final Map<String, QuizInfo> _invisible_quiz_info_map;
	private Dict _dict;
	private final QuizDict _qdict;

	private final EntrySelectionDialogData _entry_selection_data;
	private JEditorPane _html_panel;
	private JLabel _select_words_label;
	private LabeledComboBox _quiz_info_box;
	private final ActionHandler _quiz_info_box_listener = new ActionHandler();

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			JVLT.getRuntimeProperties().put("selected_quiz_type",
					_quiz_info_box.getSelectedItem());
			update();
		}
	}

	public StatsDescriptor(QuizModel model) {
		super(model);

		_quiz_info_map = new HashMap<String, QuizInfo>();
		_visible_quiz_info_map = new HashMap<String, QuizInfo>();
		_invisible_quiz_info_map = new HashMap<String, QuizInfo>();

		JVLTModel jm = model.getJVLTModel();
		_entry_selection_data = new EntrySelectionDialogData(jm);

		_dict = null;
		_qdict = new QuizDict(jm);
		_qdict.setIgnoreBatches(JVLT.getConfig().getBooleanProperty(
				"ignore_batches", false));

		init();
		loadQuizInfoList();
	}

	@Override
	public String getID() {
		return "stats";
	}

	public QuizDict getQuizDict() {
		return _qdict;
	}

	public int getSelectedEntries() {
		return _qdict.getAvailableEntryCount();
	}

	public QuizInfo getQuizInfo() {
		Object name = _quiz_info_box.getSelectedItem();
		QuizInfo[] default_quiz_infos = QuizInfo.getDefaultQuizInfos();
		for (QuizInfo defaultQuizInfo : default_quiz_infos) {
			if (name.equals(defaultQuizInfo.getName())) {
				return defaultQuizInfo;
			}
		}

		return _quiz_info_map.get(name);
	}

	/**
	 * Updates the list of available entries and refreshes the view. This
	 * function must not be called during a quiz.
	 */
	void update() {
		updateQuizDict();
		updateView();
	}

	public void dictUpdated(DictUpdateEvent event) {
		if (event instanceof NewDictDictUpdateEvent) {
			_dict = ((NewDictDictUpdateEvent) event).getDict();
			loadQuizInfoList();
			updateEntrySelectionDialog();
			update();
		} else if (event instanceof LanguageDictUpdateEvent) {
			loadQuizInfoList();
			updateEntrySelectionDialog();
			update();
		} else if (event instanceof EntryDictUpdateEvent) {
			/* Update quiz dictionary */
			EntryDictUpdateEvent entry_event = (EntryDictUpdateEvent) event;
			int type = entry_event.getType();
			switch (type) {
			case EntryDictUpdateEvent.ENTRIES_ADDED:
				_qdict.update(entry_event.getEntries(), null, null);
				break;
			case EntryDictUpdateEvent.ENTRIES_CHANGED:
				_qdict.update(null, entry_event.getEntries(), null);
				break;
			case EntryDictUpdateEvent.ENTRIES_REMOVED:
				_qdict.update(null, null, entry_event.getEntries());
				break;
			}

			/* Update view */
			updateView();

			/* Enable/disable "Next" button */
			_model.panelDescriptorUpdated();
		}
	}

	public void actionPerformed(ActionEvent ev) {
		Frame frame = JOptionPane.getFrameForComponent(_panel);
		if (ev.getActionCommand().equals("select_words")) {
			// Do not use CustomDialog.showDialog() as there will be a
			// subdialog.
			CustomDialog dlg = new CustomDialog(_entry_selection_data, frame,
					I18nService.getString("Labels", "select_words"));
			GUIUtils.showDialog(frame, dlg);
			EntrySelectionDialogData.State oldstate = _entry_selection_data
					.getState();
			if (dlg.getStatus() == AbstractDialog.OK_OPTION) {
				update();
				EntrySelectionDialogData.State state = _entry_selection_data
						.getState();
				EntrySelectionDialogData.State[] states = (EntrySelectionDialogData.State[]) JVLT
						.getRuntimeProperties().get("quiz_entry_filters");
				ArrayList<EntrySelectionDialogData.State> statelist = new ArrayList<EntrySelectionDialogData.State>();
				if (states != null) {
					statelist.addAll(Arrays.asList(states));
				}

				Iterator<EntrySelectionDialogData.State> it = statelist
						.iterator();
				while (it.hasNext()) {
					if (DefaultComparator.getInstance().compare(
							it.next().getLanguage(), state.getLanguage()) == 0) {
						it.remove();
						break;
					}
				}
				statelist.add(state);
				JVLT
						.getRuntimeProperties()
						.put(
								"quiz_entry_filters",
								statelist
										.toArray(new EntrySelectionDialogData.State[0]));
			} else {
				// Initialize according to previous state
				_entry_selection_data.initFromState(oldstate);
			}
		} else if (ev.getActionCommand().equals("manage_quiz_types")) {
			QuizDialogData data = new QuizDialogData(((QuizModel) _model)
					.getJVLTModel());
			data.setQuizInfoList(_visible_quiz_info_map.values().toArray(
					new QuizInfo[0]));

			CustomDialog dlg = new CustomDialog(data, frame, I18nService
					.getString("Labels", "manage_quiz_types"));
			GUIUtils.showDialog(frame, dlg);
			if (dlg.getStatus() == AbstractDialog.OK_OPTION) {
				QuizInfo[] quiz_info_list = data.getQuizInfoList();
				_quiz_info_map.clear();
				_quiz_info_map.putAll(_invisible_quiz_info_map);
				for (QuizInfo element : quiz_info_list) {
					String name = element.getName();
					_quiz_info_map.put(name, element);
				}

				updateQuizInfoList();
				JVLT.getRuntimeProperties().put("quiz_types", quiz_info_list);

				// Update the quiz dictionary. This is necessary when an
				// existing quiz type was modified by the user
				updateQuizDict();
			}
		} else if (ev.getActionCommand().equals("options")) {
			boolean old_ignore_batches = _qdict.isIgnoreBatches();

			QuizOptionsDialogData data = new QuizOptionsDialogData();
			CustomDialog.showDialog(data, StatsDescriptor.this._panel,
					I18nService.getString("Labels", "quiz_options"));
			_qdict.setIgnoreBatches(JVLT.getConfig().getBooleanProperty(
					"ignore_batches", false));

			if (old_ignore_batches != _qdict.isIgnoreBatches()) {
				update();
			}
		}
	}

	private void init() {
		_select_words_label = new JLabel();

		Action select_words_action = GUIUtils.createTextAction(this,
				"select_words");
		Action manage_quiz_types_action = GUIUtils.createTextAction(this,
				"manage_quiz_types");
		Action options_action = GUIUtils.createTextAction(this, "options");

		_quiz_info_box = new LabeledComboBox();
		_quiz_info_box.setLabel("select_quiz_type");
		_quiz_info_box.addActionListener(_quiz_info_box_listener);

		JPanel settings_panel = new JPanel();
		settings_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.anchor = GridBagConstraints.WEST;

		/* First row */
		cc.update(0, 0, 0.0, 0.0);
		settings_panel.add(_quiz_info_box.getLabel(), cc);
		cc.update(1, 0, 0.0, 0.0);
		settings_panel.add(_quiz_info_box, cc);
		cc.update(2, 0, 0.0, 0.0);
		settings_panel.add(new JButton(manage_quiz_types_action), cc);

		/* Second row */
		cc.update(0, 1, 0.0, 0.0);
		settings_panel.add(new JLabel(I18nService.getString("Labels", "options")
				+ ":"), cc);
		cc.update(1, 1, 0.0, 0.0);
		settings_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(2, 1, 0.0, 0.0);
		settings_panel.add(new JButton(options_action), cc);

		/* Third row */
		cc.update(0, 2, 0.0, 0.0);
		settings_panel.add(new JLabel(I18nService.getString("Labels",
				"select_filters")
				+ ":"), cc);
		cc.update(1, 2, 0.0, 0.0);
		settings_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(2, 2, 0.0, 0.0);
		settings_panel.add(new JButton(select_words_action), cc);

		_html_panel = new JEditorPane();
		_html_panel.setEditable(false);
		_html_panel.setContentType("text/html");
		JScrollPane spane = new JScrollPane(_html_panel);
		spane.setPreferredSize(new Dimension(400, 300));

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 1.0, 2, 1);
		_panel.add(spane, cc);
		cc.update(0, 1, 1.0, 0.0, 1, 1);
		_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 1, 0.0, 0.0, 1, 1);
		_panel.add(settings_panel, cc);
		cc.update(0, 2, 1.0, 0.0, 2, 1);
		_panel.add(_select_words_label, cc);
	}

	private synchronized void updateEntrySelectionDialog() {
		EntrySelectionDialogData.State[] states = (EntrySelectionDialogData.State[]) JVLT
				.getRuntimeProperties().get("quiz_entry_filters");
		if (states != null) {
			int i;
			for (i = 0; i < states.length; i++) {
				if (DefaultComparator.getInstance().compare(
						states[i].getLanguage(), _dict.getLanguage()) == 0) {
					_entry_selection_data.initFromState(states[i]);
					break;
				}
			}

			if (i == states.length) {
				_entry_selection_data
						.initFromState(new EntrySelectionDialogData.State());
			}
		} else {
			_entry_selection_data
					.initFromState(new EntrySelectionDialogData.State());
		}
	}

	private synchronized void updateQuizDict() {
		QuizInfo info = getQuizInfo();
		ObjectQuery[] oqs = _entry_selection_data.getObjectQueries();
		EntryFilter[] filters = new EntryFilter[oqs.length];
		for (int i = 0; i < oqs.length; i++) {
			filters[i] = new EntryFilter(oqs[i]);
		}

		_qdict.update(filters, info);
		_model.panelDescriptorUpdated();
	}

	private synchronized void updateView() {
		Font font = ((UIConfig) JVLT.getConfig()).getFontProperty("html_font");
		GregorianCalendar now = new GregorianCalendar();
		Collection<Entry> entries = _dict.getEntries();
		int num_entries = entries.size();
		int num_never_quizzed = 0;
		int total_num_quizzed = 0;
		int total_num_mistakes = 0;
		int not_expired = 0;
		int max_batch = 0;
		Map<Integer, Integer> batches = new HashMap<Integer, Integer>();
		Map<Integer, Integer> expired = new HashMap<Integer, Integer>();
		for (Entry entry : entries) {
			int batch = entry.getBatch();
			int num;

			if (batch > max_batch) {
				max_batch = batch;
			}

			if (entry.getNumQueried() == 0) {
				num_never_quizzed++;
			}

			total_num_quizzed += entry.getNumQueried();
			total_num_mistakes += entry.getNumMistakes();

			num = batches.containsKey(batch) ? batches.get(batch) : 0;
			batches.put(batch, num + 1);
			if (batch > 0) {
				Calendar expire_date = entry.getExpireDate();
				if (expire_date == null || expire_date.before(now)) {
					num = expired.containsKey(batch) ? expired.get(batch) : 0;
					expired.put(batch, num + 1);
				} else {
					not_expired++;
				}
			}
		}
		int num_expired = num_entries - num_never_quizzed - not_expired;

		String num_entries_str = String.valueOf(num_entries);
		String num_never_quizzed_str = String.valueOf(num_never_quizzed);
		String num_expired_str = num_expired + "/" + not_expired;
		DecimalFormat df = new DecimalFormat();
		df.setMaximumFractionDigits(2);
		double avg_num_quizzed = 0.0;
		if (num_entries > 0) {
			avg_num_quizzed = ((double) total_num_quizzed) / num_entries;
		}
		String avg_num_quizzed_str = df.format(avg_num_quizzed);
		float mistake_ratio = 0.0f;
		if (total_num_quizzed > 0) {
			mistake_ratio = total_num_mistakes * 100.0f / total_num_quizzed;
		}
		df.setMaximumFractionDigits(1);
		String avg_mistake_ratio_str = df.format(mistake_ratio) + "%";

		StringBuffer buffer = new StringBuffer(200);
		String label;
		buffer.append("<html>\n");
		if (font == null) {
			buffer.append("<body>");
		} else {
			buffer.append("<body style=\"font-family:" + font.getFamily()
					+ "; font-size:" + font.getSize() + "pt;\">\n");
		}
		buffer.append("<table width=\"100%\">\n");
		label = I18nService.getString("Labels", "num_entries") + ":";
		buffer.append(getRowString(label, num_entries_str));
		label = I18nService.getString("Labels", "never_quizzed_entries") + ":";
		buffer.append(getRowString(label, num_never_quizzed_str));
		label = I18nService.getString("Labels", "expired_entries") + ":";
		buffer.append(getRowString(label, num_expired_str));
		label = I18nService.getString("Labels", "avg_num_quizzed") + ":";
		buffer.append(getRowString(label, avg_num_quizzed_str));
		label = I18nService.getString("Labels", "avg_mistake_ratio") + ":";
		buffer.append(getRowString(label, avg_mistake_ratio_str));
		for (int i = 0; i <= max_batch; i++) {
			if (!batches.containsKey(i) || batches.get(i) == 0) {
				continue;
			}

			label = I18nService.getString("Labels", "batch_no",
					new Integer[] { i })
					+ ":";
			ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
					"Labels", "num_words"));
			String value = formatter.format(batches.get(i));
			int num_exp = expired.containsKey(i) ? expired.get(i) : 0;
			if (i > 0) {
				value = I18nService.getString("Labels", "words_expired",
						new Object[] { value, num_exp });
			}

			buffer.append(getRowString(label, value));
		}
		buffer.append("</table>\n</body>\n</html>\n");
		_html_panel.setText(buffer.toString());

		label = I18nService.getString("Messages", "selected_words",
				new Object[] { getSelectedEntries() });
		_select_words_label.setText(label);
	}

	private String getRowString(String label, String value) {
		String str = "<tr>";
		str += "<td width=\"50%\">" + label + "</td>";
		str += "<td width=\"50%\">" + value + "</td>";
		str += "</tr>\n";

		return str;
	}

	private void loadQuizInfoList() {
		/*
		 * At this state, no quiz should be running, since the quiz dictionary
		 * will be reset.
		 */
		_quiz_info_map.clear();
		QuizInfo[] qinfos = (QuizInfo[]) JVLT.getRuntimeProperties().get(
				"quiz_types");
		if (qinfos != null) {
			for (QuizInfo qinfo : qinfos) {
				_quiz_info_map.put(qinfo.getName(), qinfo);
			}
		}

		updateQuizInfoList();
	}

	private void updateQuizInfoList() {
		JVLTModel jm = ((QuizModel) _model).getJVLTModel();
		Dict dict = jm.getDict();
		String dict_lang = dict == null ? null : dict.getLanguage();
		QuizInfo[] default_quiz_infos = QuizInfo.getDefaultQuizInfos();

		_visible_quiz_info_map.clear();
		_invisible_quiz_info_map.clear();
		_quiz_info_box.removeActionListener(_quiz_info_box_listener);
		_quiz_info_box.removeAllItems();

		for (QuizInfo defaultQuizInfo : default_quiz_infos) {
			_quiz_info_box.addItem(defaultQuizInfo.getName());
		}

		for (QuizInfo info : _quiz_info_map.values()) {
			if (info.getLanguage() == null
					|| info.getLanguage().equals(dict_lang)) {
				_visible_quiz_info_map.put(info.getName(), info);
				_quiz_info_box.addItem(info.getName());
			} else {
				_invisible_quiz_info_map.put(info.getName(), info);
			}
		}

		Object selected_quiz_type = JVLT.getRuntimeProperties().get(
				"selected_quiz_type");
		if (selected_quiz_type == null
				|| !_visible_quiz_info_map.containsKey(selected_quiz_type)) {
			_quiz_info_box.setSelectedItem(default_quiz_infos[0].getName());
		} else {
			_quiz_info_box.setSelectedItem(selected_quiz_type);
		}

		_quiz_info_box.addActionListener(_quiz_info_box_listener);
	}
}

