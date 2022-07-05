package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Frame;

import net.sourceforge.jvlt.actions.AddDictObjectAction;
import net.sourceforge.jvlt.actions.EditEntryAction;
import net.sourceforge.jvlt.core.DictException;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.utils.I18nService;

import org.apache.log4j.Logger;

public class AddEntryDialog extends AbstractEntryDialog {
	private static final long serialVersionUID = 1L;

	private static final Logger logger = Logger.getLogger(AddEntryDialog.class);

	private static final int APPLY_AND_EDIT_OPTION = USER_OPTION;

	private class DialogHandler implements DialogListener {
		public void dialogStateChanged(DialogEvent ev) {
			try {
				if (ev.getType() == APPLY_OPTION) {
					AddEntryDialog.this.apply();
					AddEntryDialog.this.init();
				} else if (ev.getType() == APPLY_AND_EDIT_OPTION) {
					AddEntryDialog.this.apply();
					Entry e = getCurrentEntry().createDeepCopy();
					e.setID(AddEntryDialog.this.model.getDict()
							.getNextUnusedEntryID());
					AddEntryDialog.this.init(e);
				} else if (ev.getType() == CLOSE_OPTION) {
					setVisible(false);
				}
			} catch (InvalidDataException e) {
				MessageDialog.showDialog(getContentPane(),
						MessageDialog.WARNING_MESSAGE, e.getMessage());
			}
		}
	}

	public AddEntryDialog(Frame owner, String title, JVLTModel model) {
		super(owner, title, model);

		setButtons(new int[] { APPLY_OPTION, APPLY_AND_EDIT_OPTION,
				CLOSE_OPTION });
		addDialogListener(new DialogHandler());
	}

	@Override
	public void init() {
		super.init();
		init(new Entry(model.getDict().getNextUnusedEntryID()));
	}

	public void init(Entry entry) {
		// Initialize with empty entry. Use the lesson of the entry last added
		if (getCurrentEntry() != null) {
			entry.setLesson(getCurrentEntry().getLesson());
		}

		setCurrentEntry(entry);
	}

	@Override
	protected String getFieldNameForCustomValue(int value) {
		if (value == APPLY_AND_EDIT_OPTION) {
			return "APPLY_AND_EDIT_OPTION";
		}
		return super.getFieldNameForCustomValue(value);
	}

	@Override
	protected int getValueForCustomFieldName(String name) {
		if ("APPLY_AND_EDIT_OPTION".equals(name)) {
			return APPLY_AND_EDIT_OPTION;
		}
		return super.getValueForCustomFieldName(name);
	}

	private void apply() throws InvalidDataException {
		updateEntries();

		// Apply sense actions
		EditEntryAction eea = new EditEntryAction(getCurrentEntry(),
				getCurrentEntry());
		eea.addSenseActions(getMeaningActions());
		try {
			eea.executeAction();
		} catch (DictException ex) {
			// TODO write a message about what happened
			logger.error(ex);
		}

		// Create and execute action
		AddDictObjectAction action = new AddDictObjectAction(getCurrentEntry());
		action.setMessage(I18nService.getString("Actions", "add_entry"));
		model.getDictModel().executeAction(action);
	}
}
