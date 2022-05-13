package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.util.Collection;
import java.util.Collections;

import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.utils.I18nService;

public class EditSenseDialogData extends SenseDialogData {
	protected Sense _orig_sense;
	
	public EditSenseDialogData(JVLTModel model,
			Collection<Sense> existing_senses, Sense sense) {
		super(model, existing_senses, (Sense) sense.clone());
		
		_orig_sense = sense;
	}
	
	@Override
	protected void check(Sense sense) throws InvalidDataException {
		int index = Collections.binarySearch(_existing_senses, sense,
				new Sense.Comparator());
		if (index >= 0) {
			Sense s = _existing_senses.get(index);
			if (s != _orig_sense)
				throw new InvalidDataException(I18nService.getString("Messages",
				"duplicate_sense"));
		}
	}
}
