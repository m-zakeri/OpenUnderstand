package net.sourceforge.jvlt.ui.quiz;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Vector;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.StatsUpdateAction;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.quiz.QueryResult;
import net.sourceforge.jvlt.quiz.QuizDict;
import net.sourceforge.jvlt.ui.wizard.Wizard;
import net.sourceforge.jvlt.ui.wizard.WizardModel;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.I18nService;

import org.apache.log4j.Logger;

public class QuizModel extends WizardModel {
	private static final Logger logger = Logger.getLogger(WizardModel.class);

	private class DictUpdateHandler implements DictUpdateListener {
		public void dictUpdated(DictUpdateEvent event) {
			/*
			 * Notify panel descriptors
			 */
			for (WizardPanelDescriptor d : _descriptor_map.values()) {
				if (d instanceof EntryDescriptor) {
					((EntryDescriptor) d).dictUpdated(event);
				} else if (d instanceof StatsDescriptor) {
					((StatsDescriptor) d).dictUpdated(event);
				}
			}

			/*
			 * Notify the wizard after all panel descriptors have been updated.
			 */
			if (event instanceof EntryDictUpdateEvent
					&& event.getType() == EntryDictUpdateEvent.ENTRIES_REMOVED) {
				if (_current_descriptor instanceof EntryDescriptor
						&& ((EntryDescriptor) _current_descriptor).getEntry() == null) {
					/*
					 * If the currently displayed entry has been removed, the
					 * EntryDescriptor's dictUpdated() method already has set
					 * its current entry to null. In this case the
					 * EntryNullDescriptor is shown.
					 */
					WizardPanelDescriptor old_descriptor = _current_descriptor;
					_current_descriptor = getPanelDescriptor("entry_null");
					_wizard.newPanelDescriptorSelected(old_descriptor,
							_current_descriptor);
				} else {
					/* Update buttons */
					_wizard.panelDescriptorUpdated();
				}
			}
		}
	}

	private final JVLTModel _model;
	private QuizDict _qdict;
	private boolean _repeat_mode;
	private Entry[] _known_entries;
	private Entry[] _notknown_entries;
	private final Map<Entry, Integer> _flag_map;

	public QuizModel(JVLTModel model, SelectionNotifier notifier) {
		_model = model;
		_qdict = null;
		_repeat_mode = false;
		_known_entries = new Entry[0];
		_notknown_entries = new Entry[0];
		_flag_map = new HashMap<Entry, Integer>();

		WizardPanelDescriptor d = new StatsDescriptor(this);
		registerPanelDescriptor(d);
		_current_descriptor = d;
		d = new EntryInputDescriptor(this, notifier);
		registerPanelDescriptor(d);
		d = new EntryQuestionDescriptor(this, notifier);
		registerPanelDescriptor(d);
		d = new EntryInputAnswerDescriptor(this, notifier);
		registerPanelDescriptor(d);
		d = new EntryAnswerDescriptor(this, notifier);
		registerPanelDescriptor(d);
		d = new RepeatDescriptor(this);
		registerPanelDescriptor(d);
		d = new ResultDescriptor(this);
		registerPanelDescriptor(d);
		d = new EntryNullDescriptor(this);
		registerPanelDescriptor(d);

		DictUpdateHandler handler = new DictUpdateHandler();
		model.getDictModel().addDictUpdateListener(handler);
		model.getQueryModel().addDictUpdateListener(handler);
	}

	@Override
	public String getButtonText(String button_command) {
		if (_current_descriptor.getID().equals("stats")) {
			if (button_command.equals(Wizard.NEXT_COMMAND)) {
				return I18nService.getString("Actions", "start");
			}
		} else {
			if (button_command.equals(Wizard.CANCEL_COMMAND)) {
				return I18nService.getString("Actions", "finish");
			}
		}

		return super.getButtonText(button_command);
	}

	@Override
	public boolean isButtonEnabled(String button_command) {
		if (_current_descriptor.getID().equals("stats")) {
			StatsDescriptor sd = (StatsDescriptor) _current_descriptor;
			return button_command.equals(Wizard.NEXT_COMMAND)
					&& sd.getSelectedEntries() > 0;
		} else if (_current_descriptor.getID().equals("entry_question")) {
			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return _qdict.hasPreviousEntry();
			}
			return true;
		} else if (_current_descriptor.getID().equals("entry_input")) {
			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return _qdict.hasPreviousEntry();
			} else if (button_command.equals(Wizard.NEXT_COMMAND)) {
				EntryInputDescriptor eid = (EntryInputDescriptor) _current_descriptor;
				if (!eid.isAnswerKnown()) {
					return true;
				}
				return (eid.getAnswer().length == eid.getNumberOfQuestions());
			}
		} else if (_current_descriptor.getID().equals("entry_answer")) {
			EntryAnswerDescriptor ead = (EntryAnswerDescriptor) _current_descriptor;

			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return _qdict.hasPreviousEntry();
			} else if (button_command.equals(Wizard.NEXT_COMMAND)) {
				if (!_qdict.hasNextEntry()) {
					return false;
				}
				return (ead.getState() != YesNoPanel.UNKNOWN_OPTION);
			}
		} else if (_current_descriptor.getID().equals("entry_input_answer")) {
			if (button_command.equals(Wizard.BACK_COMMAND)) {
				return _qdict.hasPreviousEntry();
			} else if (button_command.equals(Wizard.NEXT_COMMAND)) {
				return _qdict.hasNextEntry();
			}
		} else if (_current_descriptor.getID().equals("repeat")) {
			if (button_command.equals(Wizard.CANCEL_COMMAND)) {
				return false;
			} else if (button_command.equals(Wizard.BACK_COMMAND)) {
				return true;
			} else if (button_command.equals(Wizard.NEXT_COMMAND)) {
				RepeatDescriptor rd = (RepeatDescriptor) _current_descriptor;
				return (rd.getState() != YesNoPanel.UNKNOWN_OPTION);
			}
		} else if (_current_descriptor.getID().equals("result")) {
			if (button_command.equals(Wizard.NEXT_COMMAND)) {
				return false;
			} else if (button_command.equals(Wizard.CANCEL_COMMAND)) {
				ResultDescriptor rd = (ResultDescriptor) _current_descriptor;
				return (rd.getState() != YesNoPanel.UNKNOWN_OPTION);
			}
		} else if (_current_descriptor.getID().equals("entry_null")) {
			return button_command.equals(Wizard.NEXT_COMMAND);
		}

		return super.isButtonEnabled(button_command);
	}

	@Override
	public String getStatusString() {
		if (_current_descriptor instanceof EntryQuestionDescriptor
				|| _current_descriptor instanceof EntryInputDescriptor
				|| _current_descriptor instanceof EntryAnswerDescriptor
				|| _current_descriptor instanceof EntryInputAnswerDescriptor
				|| _current_descriptor instanceof RepeatDescriptor) {
			int words = _qdict.getResultCount();
			int known = _qdict.getKnownEntries().length;
			int not_known = words - known;
			ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
					"Labels", "num_words"));
			String s = formatter.format(words);

			return I18nService.getString("Messages", "quizzed_words",
					new Object[] { s, known, not_known });
		}
		return super.getStatusString();
	}

	@Override
	public WizardPanelDescriptor nextPanelDescriptor(String command) {
		WizardPanelDescriptor next = null;

		if (_current_descriptor instanceof StatsDescriptor) {
			StatsDescriptor sd = (StatsDescriptor) _current_descriptor;
			_qdict = sd.getQuizDict();
			_qdict.start(); /* Start a new quiz */
			_repeat_mode = false;
			_known_entries = new Entry[0];
			_notknown_entries = new Entry[0];

			if (JVLT.getConfig().getBooleanProperty("input_answer", false)) {
				next = getPanelDescriptor("entry_input");
			} else {
				next = getPanelDescriptor("entry_question");
			}
		} else if (_current_descriptor instanceof EntryAnswerDescriptor
				|| _current_descriptor instanceof EntryInputAnswerDescriptor) {
			boolean input = true;
			if (_current_descriptor instanceof EntryAnswerDescriptor) {
				input = false;
			}

			/* Save current entry's flags */
			saveEntry((EntryDescriptor) _current_descriptor);

			if (command.equals(Wizard.NEXT_COMMAND)) {
				if (!input) {
					saveResult(_current_descriptor);
				}

				/* Switch to next entry */
				Entry entry = _qdict.nextEntry();

				if (_qdict.getResult(entry) == null) {
					next = getPanelDescriptor(input ? "entry_input"
							: "entry_question");
				} else {
					next = getPanelDescriptor(input ? "entry_input_answer"
							: "entry_answer");
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				if (input) {
					next = getPanelDescriptor("entry_input_answer");
				} else {
					next = getPanelDescriptor("entry_answer");
				}

				/* Switch to previous entry */
				_qdict.previousEntry();
			} else if (command.equals(Wizard.CANCEL_COMMAND)) {
				if (!input) {
					saveResult(_current_descriptor);
				}
				if (_qdict.getNotKnownEntries().length > 0) {
					next = getPanelDescriptor("repeat");
				} else if (!_repeat_mode && _qdict.getResultCount() == 0) {
					next = getPanelDescriptor("stats");
				} else {
					next = getPanelDescriptor("result");
				}
			}
		} else if (_current_descriptor instanceof EntryQuestionDescriptor
				|| _current_descriptor instanceof EntryInputDescriptor) {
			boolean input = false;
			if (_current_descriptor instanceof EntryInputDescriptor) {
				input = true;
			}

			if (command.equals(Wizard.NEXT_COMMAND)) {
				if (input) {
					saveResult(_current_descriptor);
					next = getPanelDescriptor("entry_input_answer");
				} else {
					next = getPanelDescriptor("entry_answer");
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				if (input) {
					next = getPanelDescriptor("entry_input_answer");
				} else {
					next = getPanelDescriptor("entry_answer");
				}

				/* Switch to previous entry */
				_qdict.previousEntry();
			} else if (command.equals(Wizard.CANCEL_COMMAND)) {
				if (_qdict.getNotKnownEntries().length > 0) {
					next = getPanelDescriptor("repeat");
				} else if (!_repeat_mode && _qdict.getResultCount() == 0) {
					next = getPanelDescriptor("stats");
				} else {
					next = getPanelDescriptor("result");
				}
			}
		} else if (_current_descriptor instanceof RepeatDescriptor) {
			if (command.equals(Wizard.NEXT_COMMAND)) {
				RepeatDescriptor rd = (RepeatDescriptor) _current_descriptor;
				if (rd.getState() == YesNoPanel.NO_OPTION) {
					next = getPanelDescriptor("result");
				} else {
					if (JVLT.getConfig().getBooleanProperty("input_answer",
							false)) {
						next = getPanelDescriptor("entry_input");
					} else {
						next = getPanelDescriptor("entry_question");
					}

					if (!_repeat_mode) {
						_known_entries = _qdict.getKnownEntries();
						_notknown_entries = _qdict.getNotKnownEntries();
					}
					_repeat_mode = true;
					_qdict.reset();
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				if (JVLT.getConfig().getBooleanProperty("input_answer", false)) {
					next = getPanelDescriptor("entry_input_answer");
				} else {
					next = getPanelDescriptor("entry_answer");
				}
			}
		} else if (_current_descriptor instanceof ResultDescriptor) {
			if (command.equals(Wizard.CANCEL_COMMAND)) {
				next = getPanelDescriptor("stats");

				ResultDescriptor rd = (ResultDescriptor) _current_descriptor;
				if (rd.getState() == YesNoPanel.YES_OPTION) {
					StatsUpdateAction sua = createStatsUpdateAction(
							rd.getKnownEntries(), rd.getNotKnownEntries(),
							rd.getFlagMap());
					_model.getQueryModel().executeAction(sua);
				}
			} else if (command.equals(Wizard.BACK_COMMAND)) {
				if (_qdict.getNotKnownEntries().length > 0) {
					next = getPanelDescriptor("repeat");
				} else {
					if (JVLT.getConfig().getBooleanProperty("input_answer",
							false)) {
						next = getPanelDescriptor("entry_input_answer");
					} else {
						next = getPanelDescriptor("entry_answer");
					}
				}
			}
			// NEXT_COMMAND is disabled.
		} else if (_current_descriptor instanceof EntryNullDescriptor) {
			boolean input = JVLT.getConfig().getBooleanProperty("input_answer",
					false);
			Entry entry = _qdict.getCurrentEntry();

			if (entry == null) { /* No entry left */
				if (_qdict.getNotKnownEntries().length > 0) {
					next = getPanelDescriptor("repeat");
				} else if (!_repeat_mode && _qdict.getResultCount() == 0) {
					next = getPanelDescriptor("stats");
				} else {
					next = getPanelDescriptor("result");
				}
			} else {
				if (_qdict.getResult(entry) != null) {
					next = getPanelDescriptor(input ? "entry_input_answer"
							: "entry_answer");
				} else {
					next = getPanelDescriptor(input ? "entry_input"
							: "entry_question");
				}
			}
		}

		if (next instanceof StatsDescriptor) {
			_qdict = null;
			((StatsDescriptor) next).update();
		} else if (next instanceof EntryQuestionDescriptor) {
			EntryQuestionDescriptor eqd = (EntryQuestionDescriptor) next;
			Entry entry = _qdict.getCurrentEntry();
			loadEntry(eqd, entry);
			eqd.setQuizInfo(_qdict.getQuizInfo());
		} else if (next instanceof EntryInputDescriptor) {
			EntryInputDescriptor eid = (EntryInputDescriptor) next;
			Entry entry = _qdict.getCurrentEntry();
			loadEntry(eid, entry);
			eid.setQuizInfo(_qdict.getQuizInfo());
		} else if (next instanceof EntryAnswerDescriptor) {
			loadResult(next);
			EntryAnswerDescriptor ead = (EntryAnswerDescriptor) next;
			Entry entry = _qdict.getCurrentEntry();
			loadEntry(ead, entry);
			ead.setQuizInfo(_qdict.getQuizInfo());
		} else if (next instanceof EntryInputAnswerDescriptor) {
			loadResult(next);
			EntryInputAnswerDescriptor d = (EntryInputAnswerDescriptor) next;
			Entry entry = _qdict.getCurrentEntry();
			loadEntry(d, entry);
			d.setQuizInfo(_qdict.getQuizInfo());
		} else if (next instanceof RepeatDescriptor) {
			if (!(_current_descriptor instanceof ResultDescriptor)) {
				RepeatDescriptor rd = (RepeatDescriptor) next;
				rd.setState(YesNoPanel.UNKNOWN_OPTION);
			}
		} else if (next instanceof ResultDescriptor) {
			ResultDescriptor rd = (ResultDescriptor) next;
			rd.setState(YesNoPanel.UNKNOWN_OPTION);
			if (!_repeat_mode) {
				_known_entries = _qdict.getKnownEntries();
				_notknown_entries = _qdict.getNotKnownEntries();
			}
			rd.setKnownEntries(_known_entries);
			rd.setNotKnownEntries(_notknown_entries);
		}

		/* play audio */
		if ((next instanceof EntryAnswerDescriptor)
				|| (next instanceof EntryInputAnswerDescriptor)) {
			if (JVLT.getConfig().getBooleanProperty("Quiz.PlayAudio", false)) {
				try {
					MultimediaUtils.playAudioFiles(_qdict.getCurrentEntry());
				} catch (IOException e) {
					logger.error("Playing audio failed", e);
				}
			}
		}

		_current_descriptor = next;
		return _current_descriptor;
	}

	public JVLTModel getJVLTModel() {
		return _model;
	}

	public boolean existsUnfinishedQuiz() {
		return !(_current_descriptor instanceof StatsDescriptor);
	}

	public void saveQuizResults() {
		Entry[] known;
		Entry[] notknown;
		Map<Entry, Integer> flag_map = null;
		if (_current_descriptor instanceof ResultDescriptor) {
			ResultDescriptor rd = (ResultDescriptor) _current_descriptor;
			known = rd.getKnownEntries();
			notknown = rd.getNotKnownEntries();
			flag_map = rd.getFlagMap();
		} else if (!_repeat_mode) {
			known = _qdict.getKnownEntries();
			notknown = _qdict.getNotKnownEntries();
		} else {
			known = _known_entries;
			notknown = _notknown_entries;
		}

		StatsUpdateAction sua = createStatsUpdateAction(
				known, notknown, flag_map);
		_model.getQueryModel().executeAction(sua);
	}

	@Override
	public void panelDescriptorUpdated() {
		_qdict = ((StatsDescriptor) getPanelDescriptor("stats")).getQuizDict();

		super.panelDescriptorUpdated();
	}

	private void saveResult(WizardPanelDescriptor d) {
		QueryResult result = null;
		Entry entry = _qdict.getCurrentEntry();

		if (entry == null) {
			return;
		}

		if (d instanceof EntryAnswerDescriptor) {
			EntryAnswerDescriptor ead = (EntryAnswerDescriptor) d;
			if (ead.getState() == YesNoPanel.YES_OPTION) {
				result = new QueryResult(entry, true);
			} else if (ead.getState() == YesNoPanel.NO_OPTION) {
				result = new QueryResult(entry, false);
			}
		} else if (d instanceof EntryInputDescriptor) {
			String attr_names[] = _qdict.getQuizInfo().getQuizzedAttributes();
			Vector<String> solutions = new Vector<String>();
			for (String attrName : attr_names) {
				Attribute attr = _model.getDictModel().getMetaData(Entry.class)
						.getAttribute(attrName);

				String solution = attr.getFormattedValue(entry);

				// Strip leading and trailing blank spaces
				solution = solution.replaceAll("^\\s+", "");
				solution = solution.replaceAll("\\s+$", "");

				if (solution.equals("")) {
					continue;
				}

				solutions.add(solution);
			}

			EntryInputDescriptor eid = (EntryInputDescriptor) d;
			String answers[] = eid.getAnswer();
			boolean match_case = JVLT.getConfig().getBooleanProperty(
					"match_case", true);

			if (!eid.isAnswerKnown()) {
				result = new QueryResult(entry, false);
			} else if (answers.length < solutions.size()) {
				result = new QueryResult(entry, false);
			} else {
				String bad_answers = "";
				String good_answers = "";
				String answers_delimiter = JVLT.getConfig().getProperty(
						"answers_delimiter", ",");
				for (int i = 0; i < answers.length; i++) {
					boolean correct_answer = (match_case
							&& answers[i].equals(solutions.get(i)) || (!match_case && answers[i]
							.toLowerCase().equals(
									solutions.get(i).toLowerCase())));

					if (!correct_answer) {
						if (!"".equals(bad_answers)) {
							bad_answers += answers_delimiter;
						}
						bad_answers += answers[i];
					} else {
						if (!"".equals(good_answers)) {
							good_answers += answers_delimiter;
						}
						good_answers += answers[i];
					}
				}
				if (!"".equals(bad_answers)) {
					result = new QueryResult(entry, false, bad_answers);
				} else {
					result = new QueryResult(entry, true, good_answers);
				}
			}
		}

		if (result != null) {
			_qdict.setResult(entry, result);
		}
	}

	/**
	 * @param n Next descriptor
	 */
	private void loadResult(WizardPanelDescriptor n) {
		QueryResult result = _qdict.getResult(_qdict.getCurrentEntry());
		if (n instanceof EntryAnswerDescriptor) {
			EntryAnswerDescriptor ead = (EntryAnswerDescriptor) n;
			if (result == null) {
				String default_answer = JVLT.getConfig().getProperty(
						"default_answer", "");
				if ("yes".equals(default_answer)) {
					ead.setState(YesNoPanel.YES_OPTION);
				} else if ("no".equals(default_answer)) {
					ead.setState(YesNoPanel.NO_OPTION);
				} else {
					ead.setState(YesNoPanel.UNKNOWN_OPTION);
				}
			} else if (result.isKnown()) {
				ead.setState(YesNoPanel.YES_OPTION);
			} else {
				ead.setState(YesNoPanel.NO_OPTION);
			}
		} else if (n instanceof EntryInputAnswerDescriptor) {
			EntryInputAnswerDescriptor eiad = (EntryInputAnswerDescriptor) n;
			eiad.setResult(result);
		}
	}

	private void loadEntry(EntryDescriptor ed, Entry entry) {
		ed.setEntry(entry);
		ed
				.setUserFlags(_flag_map.containsKey(entry) ? _flag_map
						.get(entry) : 0);
	}

	private void saveEntry(EntryDescriptor ed) {
		if (ed.getEntry() != null) {
			_flag_map.put(ed.getEntry(), ed.getUserFlags());
		}
	}

	private StatsUpdateAction createStatsUpdateAction(Entry[] known,
			Entry[] unknown, Map<Entry, Integer> flag_map) {
		StatsUpdateAction sua = new StatsUpdateAction(known, unknown);
		sua.setUpdateBatches(!_qdict.isIgnoreBatches() ||
				JVLT.getConfig().getBooleanProperty("update_batches", false));
		sua.setMessage(I18nService.getString("Actions", "save_quiz_results"));

		/*
		 * Store flags. First, the flags specified by the user during the quiz
		 * are stored, afterwards those flags set in the result tables. 
		 */
		for (Entry e : _flag_map.keySet()) {
			sua.setUserFlag(e, _flag_map.get(e));
		}
		if (flag_map != null) {
			for (Map.Entry<Entry, Integer> e: flag_map.entrySet()) {
				sua.setUserFlag(e.getKey(), e.getValue());
			}
		}

		return sua;
	}
}

