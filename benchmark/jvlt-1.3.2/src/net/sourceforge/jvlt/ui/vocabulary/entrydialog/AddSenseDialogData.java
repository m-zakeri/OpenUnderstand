package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.util.Collection;
import java.util.Collections;

import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.utils.I18nService;

public class AddSenseDialogData extends SenseDialogData {
	public AddSenseDialogData(JVLTModel model,
			Collection<Sense> existing_senses) {
		super(model, existing_senses, new Sense());
	}
	
	@Override
	protected void check(Sense sense) throws InvalidDataException {
		if (Collections.binarySearch(
				_existing_senses, sense, new Sense.Comparator()) >= 0) {
			throw new InvalidDataException(I18nService.getString("Messages",
					"duplicate_sense"));
		}
	}
}
