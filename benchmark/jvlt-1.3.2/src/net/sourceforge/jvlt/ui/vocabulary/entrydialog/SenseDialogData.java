package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.GridBagLayout;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;

import javax.swing.JPanel;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;

import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.core.StringPair;
import net.sourceforge.jvlt.metadata.ChoiceAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.dialogs.CustomDialogData;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.I18nService;

public abstract class SenseDialogData extends CustomDialogData {
	protected final JVLTModel _model;
	protected Sense _sense;
	protected List<Sense> _existing_senses = new ArrayList<Sense>();

	private CustomTextField _translation_field;
	private CustomTextField _definition_field;
	private CustomFieldPanel _custom_field_panel;

	public SenseDialogData(JVLTModel model, Collection<Sense> existing_senses,
			Sense sense) {
		_model = model;
		_sense = sense;
		
		_existing_senses.addAll(existing_senses);
		Collections.sort(_existing_senses, new Sense.Comparator());

		init();
	}

	public Sense getSense() { return _sense; }

	@Override
	public void updateData() throws InvalidDataException {
		_sense.setTranslation(_translation_field.getText());
		_sense.setDefinition(_definition_field.getText());

		/* Custom fields */
		_custom_field_panel.updateData();
		_sense.setCustomFields(_custom_field_panel.getKeyValuePairs());

		if (_sense.getTranslation().equals("")
				&& _sense.getDefinition().equals(""))
			throw new InvalidDataException(I18nService.getString("Messages",
					"no_translation_definition"));
		
		check(_sense);
	}
	
	protected abstract void check(Sense sense) throws InvalidDataException;
	
	private void init() {
		_translation_field = new CustomTextField(20);
		_translation_field.setActionCommand("translation");
		_definition_field = new CustomTextField(20);
		_definition_field.setActionCommand("definition");
		
		_custom_field_panel = new CustomFieldPanel();
		_custom_field_panel.setBorder(new TitledBorder(
				new EtchedBorder(EtchedBorder.LOWERED),
				I18nService.getLabelString("custom_fields")));
		
		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		_content_pane.add(_translation_field.getLabel(), cc);
		cc.update(0, 1);
		_content_pane.add(_definition_field.getLabel(), cc);
		cc.update(1, 0);
		_content_pane.add(_translation_field, cc);
		cc.update(1, 1);
		_content_pane.add(_definition_field, cc);
		cc.update(0, 2, 1.0, 1.0, 2, 1);
		_content_pane.add(_custom_field_panel, cc);
		
		// ----------
		// Init data.
		// ----------
		_translation_field.setText(_sense.getTranslation());
		_definition_field.setText(_sense.getDefinition());
		MetaData data = _model.getDictModel().getMetaData(Sense.class);
		
		ChoiceAttribute custom_field_attr =
			(ChoiceAttribute) data.getAttribute("CustomFields");
		_custom_field_panel.setKeyValuePairs(_sense.getCustomFields());
		
		HashSet<String> choices = new HashSet<String>();
		for (Object o: custom_field_attr.getValues()) {
			choices.add(o.toString());
		}
		for (Sense s: _existing_senses) {
			for (StringPair p: s.getCustomFields()) {
				choices.add(p.getFirst());
			}
		}
		_custom_field_panel.setChoices(choices.toArray(new String[0]));
	}
}
