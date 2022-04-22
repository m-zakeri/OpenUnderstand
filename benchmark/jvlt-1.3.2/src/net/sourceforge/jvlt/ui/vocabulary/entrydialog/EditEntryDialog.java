package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Frame;
import java.util.ArrayList;
import java.util.List;

import net.sourceforge.jvlt.actions.EditEntriesAction;
import net.sourceforge.jvlt.actions.EditEntryAction;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.utils.I18nService;

public class EditEntryDialog extends AbstractEntryDialog {
	private static final long serialVersionUID = 1L;

	private class DialogHandler implements DialogListener {
		public void dialogStateChanged(DialogEvent ev) {
			if (ev.getType() == OK_OPTION) {
				try {
					updateEntries();

					// Create action and execute it
					ArrayList<EditEntryAction> actions = new ArrayList<EditEntryAction>();
					for (int i = 0; i < newEntries.size(); i++) {
						EditEntryAction eea = new EditEntryAction(
								originalEntries.get(i), newEntries.get(i));

						// The senses can be modified only when editing
						// a single entry
						if (originalEntries.size() == 1) {
							eea.addSenseActions(getMeaningActions());
						}

						actions.add(eea);
					}
					EditEntriesAction action = new EditEntriesAction(actions
							.toArray(new EditEntryAction[actions.size()]));
					action.setMessage(I18nService.getString("Actions",
							"edit_entries", new Object[] { actions.size() }));
					model.getDictModel().executeAction(action);

					setVisible(false);
				} catch (InvalidDataException e) {
					MessageDialog.showDialog(getContentPane(),
							MessageDialog.WARNING_MESSAGE, e.getMessage());
				}
			} else if (ev.getType() == CANCEL_OPTION) {
				setVisible(false);
			}
		}
	}

	private List<Entry> originalEntries = new ArrayList<Entry>();
	private final List<Entry> newEntries = new ArrayList<Entry>();

	public EditEntryDialog(Frame owner, String title, JVLTModel model) {
		super(owner, title, model);

		setButtons(new int[] { OK_OPTION, CANCEL_OPTION });
		addDialogListener(new DialogHandler());
	}

	public void init(List<Entry> entries) {
		super.init();

		originalEntries = entries;
		newEntries.clear();
		for (Entry entry : originalEntries) {
			newEntries.add((Entry) entry.clone());
		}

		setCurrentEntry(newEntries);
	}
}
