package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.Font;
import java.util.List;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.metadata.DefaultAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.ui.table.CustomFontCellRenderer;
import net.sourceforge.jvlt.ui.table.SortableTable;
import net.sourceforge.jvlt.ui.table.SortableTableModel;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.Utils;

public class ExampleSenseTable extends SortableTable<Example.TextFragment> {
	private static class TextFragmentMetaData extends MetaData {
		private static class OriginalAttribute extends DefaultAttribute {
			public OriginalAttribute() {
				super("Original", String.class);
			}

			@Override
			public Object getValue(Object o) {
				Example.TextFragment f = (Example.TextFragment) o;
				return f.getSense().getParent().getOrthography();
			}
		}

		private static class PronunciationAttribute extends DefaultAttribute {
			public PronunciationAttribute() {
				super("Pronunciations", String.class);
			}

			@Override
			public Object getValue(Object o) {
				Example.TextFragment f = (Example.TextFragment) o;
				return Utils.arrayToString(f.getSense().getParent()
						.getPronunciations());
			}
		}

		private static class SenseAttribute extends DefaultAttribute {
			public SenseAttribute() {
				super("Sense", String.class);
			}

			@Override
			public Object getValue(Object o) {
				Example.TextFragment f = (Example.TextFragment) o;
				return f.getSense().toString();
			}
		}

		public TextFragmentMetaData() {
			super(Example.TextFragment.class);
		}

		@Override
		protected void init() {
			addAttribute(new OriginalAttribute());
			addAttribute(new PronunciationAttribute());
			addAttribute(new SenseAttribute());
		}
	}

	private static final long serialVersionUID = 1L;

	private static final CustomFontCellRenderer ORIGINAL_RENDERER;
	private static final CustomFontCellRenderer PRONUNCIATION_RENDERER;

	static {
		Font font;
		ORIGINAL_RENDERER = new CustomFontCellRenderer();
		PRONUNCIATION_RENDERER = new CustomFontCellRenderer();
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_orth_font");
		if (font != null) {
			ORIGINAL_RENDERER.setCustomFont(font);
		}
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_pron_font");
		if (font != null) {
			PRONUNCIATION_RENDERER.setCustomFont(font);
		}
	}

	private Example example = null;

	public ExampleSenseTable(Example example) {
		super(new SortableTableModel<Example.TextFragment>(
				new TextFragmentMetaData()));

		this.example = example;

		setCellRenderer("Original", ORIGINAL_RENDERER);
		setCellRenderer("Pronunciations", PRONUNCIATION_RENDERER);
		_model.setColumnNames(_model.getMetaData().getAttributeNames());
		update();
	}

	public Example.TextFragment getSelectedTextFragment() {
		List<Example.TextFragment> fragments = getSelectedObjects();
		if (fragments.size() == 0) {
			return null;
		} else {
			return fragments.get(0);
		}
	}

	public void update() {
		_model.clear();

		for (Example.TextFragment f : example.getTextFragments()) {
			if (f.getSense() != null) {
				_model.addObject(f);
			}
		}
	}
}
