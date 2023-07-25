package net.sourceforge.jvlt.ui.quiz;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.DictUpdateListener.DictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.EntryDictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.LanguageDictUpdateEvent;
import net.sourceforge.jvlt.event.DictUpdateListener.NewDictDictUpdateEvent;
import net.sourceforge.jvlt.quiz.QuizInfo;
import net.sourceforge.jvlt.ui.vocabulary.EntryInfoPanel;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.Utils;

abstract class EntryDescriptor extends WizardPanelDescriptor {
	protected EntryInfoPanel _info_panel;
	protected QuizInfo _quiz_info;
	protected FlagPanel _flag_panel;

	public EntryDescriptor(QuizModel model, SelectionNotifier notifier) {
		super(model);
		_info_panel = new EntryInfoPanel(model.getJVLTModel(), notifier);
		_flag_panel = new FlagPanel();
		_quiz_info = null;
		init();
	}

	protected abstract void init();

	public Entry getEntry() {
		return _info_panel.getEntry();
	}

	public void setEntry(Entry entry) {
		_info_panel.setEntry(entry);
	}

	public int getUserFlags() {
		return _flag_panel.getSelectedItem().getValue();
	}

	public void setUserFlags(int flags) {
		Entry.Stats.UserFlag flag = Entry.Stats.UserFlag.NONE;

		/*
		 * Set user flag. Though there may be more than one flag set, only one
		 * is displayed.
		 */
		for (Entry.Stats.UserFlag f : Entry.Stats.UserFlag.values()) {
			if (f.getValue() != 0) {
				if ((flags & f.getValue()) != 0) {
					flag = f;
					break;
				}
			}
		}

		_flag_panel.setSelectedItem(flag);
	}

	public void setQuizInfo(QuizInfo info) {
		_quiz_info = info;
		entryAttributesUpdated();
	}

	public void dictUpdated(DictUpdateEvent event) {
		if (event instanceof NewDictDictUpdateEvent
				|| event instanceof LanguageDictUpdateEvent) {
			entryAttributesUpdated();
		} else if (event instanceof EntryDictUpdateEvent) {
			if (event.getType() == EntryDictUpdateEvent.ENTRIES_REMOVED) {
				EntryDictUpdateEvent edue = (EntryDictUpdateEvent) event;
				if (edue.getEntries().contains(getEntry())) {
					/*
					 * Set null entry so wizard knows that panels have to be
					 * switched
					 */
					setEntry(null);
				}
			}
		}
		/*
		 * Modifying entries or examples are all handled by the info panel.
		 */
	}

	protected void entryAttributesUpdated() {
		QuizModel model = (QuizModel) _model;

		Object[] displayedattrs = (Object[]) JVLT.getRuntimeProperties().get(
				"displayed_attributes");
		if (displayedattrs == null) {
			displayedattrs = model.getJVLTModel().getDictModel().getMetaData(
					Entry.class).getAttributeNames();
		}
		_info_panel.setDisplayedEntryAttributes(Utils
				.objectArrayToStringArray(displayedattrs));

		String[] exampleattrs = model.getJVLTModel().getDictModel()
				.getMetaData(Example.class).getAttributeNames();
		_info_panel.setDisplayedExampleAttributes(exampleattrs);
	}

	protected String formatAttributeList(String[] attributes) {
		AttributeResources ar = new AttributeResources();
		String attr = "";
		for (int i = 0; i < attributes.length; i++) {
			attr += ar.getString(attributes[i]);
			if (i < attributes.length - 2) {
				attr += I18nService.getString("Labels", "enumeration_delimiter");
			} else if (i == attributes.length - 2) {
				attr += I18nService.getString("Labels",
						"enumeration_delimiter_last");
			}
		}

		return attr;
	}
}
