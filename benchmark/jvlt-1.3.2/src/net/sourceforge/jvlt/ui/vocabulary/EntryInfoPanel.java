package net.sourceforge.jvlt.ui.vocabulary;

import java.util.Arrays;
import java.util.Collection;
import java.util.Vector;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.swing.event.HyperlinkEvent;

import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.SelectionListener.SelectionEvent;
import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.MultimediaFile;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.utils.DictObjectFormatter;
import net.sourceforge.jvlt.utils.XSLTransformer;

import org.apache.log4j.Logger;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class EntryInfoPanel extends InfoPanel {
	public enum Mode { NORMAL, QUIZ };

	private static final Logger logger = Logger.getLogger(EntryInfoPanel.class);
	private static final long serialVersionUID = 1L;

	private final XSLTransformer _default_transformer;
	private final XSLTransformer _quiz_transformer;
	private final Vector<Attribute> _entry_attributes = new Vector<Attribute>();
	private final Vector<Attribute> _example_attributes = new Vector<Attribute>();
	
	private Entry _current_entry = null;
	private Mode _mode = Mode.NORMAL;

	public EntryInfoPanel(JVLTModel model, SelectionNotifier notifier) {
		super(model, notifier);

		_default_transformer = createTransformer("/xml/entry.xsl");
		_quiz_transformer = createTransformer("/xml/entry-quiz.xsl");
		MetaData entry_data = model.getDictModel().getMetaData(Entry.class);
		_entry_attributes.addAll(Arrays.asList(entry_data.getAttributes()));
		MetaData example_data = model.getDictModel().getMetaData(Example.class);
		_example_attributes.addAll(Arrays.asList(example_data.getAttributes()));
	}

	public Entry getEntry() {
		return _current_entry;
	}

	public void setEntry(Entry entry) {
		_current_entry = entry;
		updateView();
	}
	
	public Mode getMode() {
		return _mode;
	}
	
	public void setMode(Mode mode) {
		_mode = mode;
	}

	public void setDisplayedEntryAttributes(String[] attr_names) {
		MetaData entry_data = _model.getDictModel().getMetaData(Entry.class);
		_entry_attributes.clear();
		for (String attrName : attr_names) {
			Attribute attr = entry_data.getAttribute(attrName);
			if (attr == null) {
				logger.warn("Attribute \"" + attrName + "\" does not exist.");
			} else {
				_entry_attributes.add(entry_data.getAttribute(attrName));
			}
		}
		updateView();
	}

	public void setDisplayedExampleAttributes(String[] attr_names) {
		MetaData example_data = _model.getDictModel()
				.getMetaData(Example.class);
		_example_attributes.clear();
		for (String attrName : attr_names) {
			Attribute attr = example_data.getAttribute(attrName);
			if (attr == null) {
				logger.warn("Warning: Attribute \"" + attrName
						+ "\" does not exist.");
			} else {
				_example_attributes.add(attr);
			}
		}
		updateView();
	}

	@Override
	public synchronized void dictUpdated(DictUpdateEvent event) {
		if (event instanceof EntryDictUpdateEvent) {
			EntryDictUpdateEvent eevent = (EntryDictUpdateEvent) event;
			if (eevent.getType() == EntryDictUpdateEvent.ENTRIES_CHANGED) {
				updateView();
			} else if (event.getType() == EntryDictUpdateEvent.ENTRIES_REMOVED) {
				if (_current_entry != null) {
					if (eevent.getEntries().contains(_current_entry)) {
						_current_entry = null;
						updateView();
					}
				}
			}
		} else if (event instanceof ExampleDictUpdateEvent) {
			updateView();
		} else if (event instanceof LanguageDictUpdateEvent) {
			_current_entry = null;
			updateView();
		} else if (event instanceof NewDictDictUpdateEvent) {
			_current_entry = null;
			updateView();
			super.dictUpdated(event);
		}
	}

	@Override
	public void hyperlinkUpdate(HyperlinkEvent ev) {
		if (ev.getEventType() == HyperlinkEvent.EventType.ACTIVATED) {
			String descr = ev.getDescription();
			if (descr.length() < 1) {
				return;
			}

			if (descr.startsWith("e")) {
				String id = descr.substring(0, descr.indexOf('-'));
				Entry entry = _dict.getEntry(id);
				if (entry != null) {
					_notifier
							.fireSelectionEvent(new SelectionEvent(entry, this));
				}
			} else if (descr.startsWith("x")) {
				Example example = _dict.getExample(descr);
				if (example != null) {
					_notifier.fireSelectionEvent(new SelectionEvent(example,
							this));
				}
			} else if (descr.startsWith("mm:")) {
				String file_name = descr.substring(3, descr.length());
				MultimediaFile file = MultimediaUtils
						.getMultimediaFileForName(file_name);
				if (file != null) {
					_notifier
							.fireSelectionEvent(new SelectionEvent(file, this));
				}
			}
		}
	}

	private void updateView() {
		if (_current_entry == null) {
			setText("");
			return;
		}

		Document doc = _builder.newDocument();
		Element root = doc.createElement("Dict");
		doc.appendChild(root);
		DictObjectFormatter dof = new DictObjectFormatter(doc);
		root.appendChild(dof.getElementForObject(_current_entry,
				_entry_attributes.toArray(new Attribute[0])));
		Collection<Example> examples = _dict.getExamples(_current_entry);
		for (Example example : examples) {
			root.appendChild(dof.getElementForObject(example,
					_example_attributes.toArray(new Attribute[0])));
			// XMLWriter writer = new XMLWriter(System.out);
			// try { writer.write(doc); }
			// catch (java.io.IOException e) { e.printStackTrace(); }
		}

		String html = _mode == Mode.NORMAL
				? _default_transformer.transform(doc)
				: _quiz_transformer.transform(doc);
		// Because of a bug in JEditorPane, the content-type meta tag causes
		// an error. Therefore, all meta tags are removed.
		Pattern p = Pattern.compile("<META[^>]+>");
		Matcher m = p.matcher(html);
		html = m.replaceAll("");
		// System.out.println(html);
		setText(html);
	}
}
