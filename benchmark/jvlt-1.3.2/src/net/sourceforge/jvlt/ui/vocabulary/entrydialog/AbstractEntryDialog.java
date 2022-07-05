package net.sourceforge.jvlt.ui.vocabulary.entrydialog;

import java.awt.Container;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.swing.Box;
import javax.swing.DefaultListModel;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JList;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.ListSelectionModel;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.AddDictObjectAction;
import net.sourceforge.jvlt.actions.DictObjectAction;
import net.sourceforge.jvlt.actions.EditDictObjectAction;
import net.sourceforge.jvlt.actions.MoveSenseAction;
import net.sourceforge.jvlt.actions.RemoveSenseAction;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.event.ComponentReplacementListener;
import net.sourceforge.jvlt.metadata.ChoiceAttribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.components.ButtonPanel;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.components.LabeledComboBox;
import net.sourceforge.jvlt.ui.components.SortedComboBoxModel;
import net.sourceforge.jvlt.ui.components.StringListEditor;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.CustomDialog;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.Utils;

/**
 * The entry dialog, used both for adding new words and editing existing ones.
 * 
 * @author henning, thrar
 */
public abstract class AbstractEntryDialog extends AbstractDialog {
	private static final long serialVersionUID = 1L;

	private final MeaningsArea meaningsArea = new MeaningsArea();

	private final TextFieldArea textFieldArea;

	protected final JVLTModel model;
	private final List<Entry> currentEntries = new ArrayList<Entry>();

	/**
	 * Creates a new instance. The GUI is automatically built. Call
	 * {@link #init()} to finalize settings before showing the dialog.
	 * 
	 * @param owner the owner window for the dialog
	 * @param title the dialog window title
	 * @param model the data model to read data from
	 */
	public AbstractEntryDialog(Frame owner, String title, JVLTModel model) {
		super(owner, title, true);
		this.model = model;
		textFieldArea = new TextFieldArea(model);

		setContent(buildUi());
	}

	/**
	 * Initializes the dialog. Call this before making it visible.
	 */
	public void init() {
		textFieldArea.setDefaultFocus();
	}

	/**
	 * Builds the entire dialog GUI.
	 * 
	 * @return the entire dialog GUI
	 */
	private Container buildUi() {
		Container background = new JPanel();
		background.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		background.add(textFieldArea.getGuiComponent(), cc);
		cc.update(0, 1, 1.0, 1.0);
		background.add(meaningsArea.getGuiComponent(), cc);
		cc.update(0, 2, 1.0, 0.0);
		background.add(buildAdvancedButtonArea(), cc);
		return background;
	}

	/**
	 * Builds the area containing the advanced button.
	 * 
	 * @return the area containing the advanced button
	 */
	private JComponent buildAdvancedButtonArea() {
		CustomAction advancedAction = GUIUtils.createTextAction(
				new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						if (e.getActionCommand().equals("advanced")) {
							CustomDialog.showDialog(getAdvancedDialogData(),
									getContentPane(), I18nService
											.getLabelString("advanced"));
						}
					}
				}, "advanced");

		JButton advancedButton = new JButton(advancedAction);

		ButtonPanel advancedButtonPanel = new ButtonPanel(
				SwingConstants.HORIZONTAL, SwingConstants.RIGHT);
		advancedButtonPanel.addButton(advancedButton);
		return advancedButtonPanel;
	}

	/**
	 * Loads general dialog information (e.g. display settings).
	 * 
	 * @param config the settings will be loaded from here
	 */
	public void loadState(UIConfig config) {
		if (config.containsKey("EntryDialog.size")) {
			getContentPane().setPreferredSize(
					config.getDimensionProperty("EntryDialog.size",
							new Dimension(400, 300)));
		}
	}

	/**
	 * Saves general dialog information (e.g. display settings).
	 * 
	 * @param config the settings will be stored here
	 */
	public void saveState(UIConfig config) {
		config.setProperty("EntryDialog.size", getContentPane().getSize());
	}

	/**
	 * Sets the entries to display in the dialog.
	 * 
	 * @param entry the entries to display in the dialog
	 */
	protected final void setCurrentEntry(Entry... entry) {
		setCurrentEntry(Arrays.asList(entry));
	}

	/**
	 * Sets the entries to display in the dialog.
	 * 
	 * @param entry the entries to display in the dialog
	 */
	protected final void setCurrentEntry(List<Entry> entry) {
		currentEntries.clear();
		currentEntries.addAll(entry);

		textFieldArea.setCurrentEntries(currentEntries);
		meaningsArea.setCurrentEntries(currentEntries);
	}

	/**
	 * Stores the data from the GUI in the underlying elements.
	 * 
	 * @throws InvalidDataException if the GUI data is inconsistent and may not
	 *             be stored in the model
	 */
	protected final void updateEntries() throws InvalidDataException {
		String lesson = textFieldArea.getSelectedLesson();
		for (Entry entry : currentEntries) {
			entry.setLesson(lesson);
		}

		if (currentEntries.size() == 1) {
			if (!meaningsArea.hasMeanings()) {
				throw new InvalidDataException(I18nService
						.getMessageString("no_sense"));
			}

			if (textFieldArea.getSelectedOrthography().equals("")) {
				throw new InvalidDataException(I18nService
						.getMessageString("empty_orthography"));
			}

			getCurrentEntry().setOrthography(
					textFieldArea.getSelectedOrthography());
			getCurrentEntry().setPronunciations(
					textFieldArea.getSelectedPronunciations());

			Entry e = model.getDict().getEntry(getCurrentEntry());
			if (e != null && !e.getID().equals(getCurrentEntry().getID())) {
				throw new InvalidDataException(I18nService
						.getMessageString("duplicate_entry"));
			}
		}
	}

	/**
	 * Builds and returns the contents of the 'advanced' dialog.
	 * 
	 * @return the contents of the 'advanced' dialog
	 */
	private AdvancedEntryDialogData getAdvancedDialogData() {
		return new AdvancedEntryDialogData(getCurrentEntries(), model);
	}

	/**
	 * Returns all currently selected entries.
	 * 
	 * @return all currently selected entries
	 */
	protected final List<Entry> getCurrentEntries() {
		return new ArrayList<Entry>(currentEntries);
	}

	/**
	 * Returns the currently selected entry if a single one is selected. If no
	 * or multiple entries are selected, <tt>null</tt> is returned.
	 * 
	 * @return the currently selected entry, or <tt>null</tt> if none or more
	 *         than one are selected
	 */
	protected final Entry getCurrentEntry() {
		if (currentEntries.size() == 1) {
			return currentEntries.get(0);
		}
		return null;
	}

	/**
	 * Returns the actions to perform regarding the entry's meanings.
	 * 
	 * @return the actions to perform regarding the entry's meanings
	 */
	protected final List<DictObjectAction> getMeaningActions() {
		return meaningsArea.getMeaningActions();
	}

	/**
	 * The GUI components of the middle part of the entry dialog, containing the
	 * word meanings list and its buttons.
	 * 
	 * @author thrar
	 */
	private class MeaningsArea {
		private final Map<Sense, Sense> meaningsMap = new HashMap<Sense, Sense>();
		private final DefaultListModel listModel = new DefaultListModel();
		private final JList meaningList = new JList(listModel);
		private final List<DictObjectAction> meaningActions = new ArrayList<DictObjectAction>();

		private final CustomAction addAction = GUIUtils.createTextAction(
				new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						SenseDialogData data = new AddSenseDialogData(
								model, meaningsMap.keySet());
						int result = CustomDialog.showDialog(data,
								getContentPane(), I18nService
										.getLabelString("add_sense"));
						if (result == AbstractDialog.OK_OPTION) {
							Sense sense = data.getSense();
							AddDictObjectAction action = new AddDictObjectAction(
									sense);
							meaningActions.add(action);
							Sense clone = (Sense) sense.clone();
							listModel.addElement(clone);
							meaningsMap.put(clone, sense);
						}
					}
				}, "add");
		private final CustomAction editAction = GUIUtils.createTextAction(
				new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						Object obj = meaningList.getSelectedValue();
						if (obj == null) {
							return;
						}

						Sense sense = (Sense) obj;
						SenseDialogData data = new EditSenseDialogData(
								model, meaningsMap.keySet(), sense);
						int result = CustomDialog.showDialog(data,
								getContentPane(), I18nService
										.getLabelString("edit_sense"));
						if (result == AbstractDialog.OK_OPTION) {
							Sense newSense = data.getSense();
							sense.reinit(newSense);
							EditDictObjectAction action = new EditDictObjectAction(
									meaningsMap.get(sense), newSense);
							meaningActions.add(action);
							meaningList.revalidate();
							meaningList.repaint(meaningList.getVisibleRect());
						}
					}
				}, "edit");
		private final CustomAction removeAction = GUIUtils.createTextAction(
				new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						int index = meaningList.getSelectedIndex();
						if (index < 0) {
							return;
						}

						Sense sense = (Sense) listModel.getElementAt(index);
						Sense orig_sense = meaningsMap.get(sense);
						/*
						 * If the parent of the sense is null, i.e. the sense
						 * has been added in this dialog, there are no examples
						 * linked to it yet.
						 */
						if (orig_sense.getParent() != null) {
							Collection<Example> linked_examples = model
									.getDict().getExamples(orig_sense);
							if (!linked_examples.isEmpty()) {
								MessageDialog
										.showDialog(
												getContentPane(),
												MessageDialog.WARNING_MESSAGE,
												I18nService
														.getMessageString("cannot_remove_sense"));
								return;
							}
						}

						int result = JOptionPane.showConfirmDialog(
								getContentPane(), I18nService
										.getMessageString("remove_sense"),
										I18nService.getLabelString("confirm"),
								JOptionPane.YES_NO_OPTION);
						if (result == JOptionPane.YES_OPTION) {
							RemoveSenseAction action = new RemoveSenseAction(
									meaningsMap.get(sense), index);
							meaningActions.add(action);
							listModel.remove(index);
							meaningsMap.remove(orig_sense);
						}
					}
				}, "remove");
		private final CustomAction meaningUpAction = GUIUtils.createIconAction(
				new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						moveSelectedElement(-1);
					}
				}, "up");
		private final CustomAction meaningDownAction = GUIUtils
				.createIconAction(new ActionListener() {
					public void actionPerformed(ActionEvent e) {
						moveSelectedElement(1);
					}
				}, "down");

		private JComponent guiComponent;

		/**
		 * Builds the meanings area of the entry dialog.
		 * 
		 * @return the meanings area of the entry dialog
		 */
		private JComponent buildMeaningsArea() {
			JButton addButton = new JButton(addAction);
			JButton editButton = new JButton(editAction);
			JButton removeButton = new JButton(removeAction);
			ButtonPanel buttonPanel = new ButtonPanel(SwingConstants.VERTICAL,
					SwingConstants.TOP);
			buttonPanel.addButton(addButton);
			buttonPanel.addButton(editButton);
			buttonPanel.addButton(removeButton);

			meaningList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
			meaningList.addListSelectionListener(new ListSelectionListener() {
				public void valueChanged(ListSelectionEvent e) {
					if (!e.getValueIsAdjusting()) {
						updateActions(getCurrentEntries());
					}
				}
			});
			JScrollPane scrpane = new JScrollPane();
			scrpane.setPreferredSize(new Dimension(300, 100));
			scrpane.getViewport().setView(meaningList);

			JPanel meaningPanel = new JPanel();
			meaningPanel.setLayout(new GridBagLayout());
			CustomConstraints cc = new CustomConstraints();
			cc.update(0, 0);
			meaningPanel.add(new JButton(meaningUpAction), cc);
			cc.update(0, 1);
			meaningPanel.add(new JButton(meaningDownAction), cc);
			cc.update(0, 2, 0.0, 1.0, 1, GridBagConstraints.REMAINDER);
			meaningPanel.add(Box.createVerticalGlue(), cc);
			cc.update(1, 0, 1.0, 1.0);
			meaningPanel.add(scrpane, cc);
			cc.update(2, 0, 0.0, 1.0);
			meaningPanel.add(buttonPanel, cc);
			meaningPanel.setBorder(new TitledBorder(new EtchedBorder(
					EtchedBorder.LOWERED),
					I18nService.getLabelString("senses")));
			return meaningPanel;
		}

		/**
		 * Moves the currently selected list element down the given amount of
		 * steps. If this amount is negative, the element is moved up instead.
		 * 
		 * @param steps number of steps to move the element
		 */
		private void moveSelectedElement(int steps) {
			int index = meaningList.getSelectedIndex();
			int newIndex = index + steps;
			Object obj = listModel.remove(index);
			listModel.add(newIndex, obj);
			meaningList.setSelectedIndex(newIndex);

			Sense sense = (Sense) obj;
			MoveSenseAction action = new MoveSenseAction(
					meaningsMap.get(sense), index, newIndex);
			meaningActions.add(action);
		}

		/**
		 * Returns the GUI component for this area, building it if necessary.
		 * 
		 * @return the GUI component for this area
		 */
		JComponent getGuiComponent() {
			if (guiComponent == null) {
				guiComponent = buildMeaningsArea();
			}
			return guiComponent;
		}

		/**
		 * Sets the currently selected entries, updating the fields as needed.
		 * 
		 * @param currentEntries the currently selected entries
		 */
		void setCurrentEntries(List<Entry> currentEntries) {
			updateComponents(currentEntries);
			updateActions(currentEntries);
		}

		/**
		 * Enables/disables actions related to this area depending on the
		 * selected elements.
		 * 
		 * @param selectedEntries the currently selected entries
		 */
		private void updateActions(List<Entry> selectedEntries) {
			if (selectedEntries.size() == 1) {
				int selectedMeaningIndex = meaningList.getSelectedIndex();
				addAction.setEnabled(true);
				editAction.setEnabled(selectedMeaningIndex >= 0);
				removeAction.setEnabled(selectedMeaningIndex >= 0);
				meaningUpAction.setEnabled(selectedMeaningIndex > 0);
				meaningDownAction.setEnabled(selectedMeaningIndex >= 0
						&& selectedMeaningIndex != listModel.getSize() - 1);
			} else {
				addAction.setEnabled(false);
				editAction.setEnabled(false);
				removeAction.setEnabled(false);
				meaningUpAction.setEnabled(false);
				meaningDownAction.setEnabled(false);
			}
		}

		/**
		 * Updates display components in this area depending on the selected
		 * elements.
		 * 
		 * @param selectedEntries the currently selected entries
		 */
		private void updateComponents(List<Entry> selectedEntries) {
			meaningsMap.clear();
			meaningActions.clear();
			listModel.clear();

			if (selectedEntries.size() == 1) {
				for (Sense meaning : getCurrentEntry().getSenses()) {
					Sense clone = (Sense) meaning.clone();
					meaningsMap.put(clone, meaning);
					listModel.addElement(clone);
				}

				meaningList.setEnabled(true);
			} else {
				meaningList.setEnabled(false);
			}
		}

		/**
		 * Checks if the meaning area's GUI currently contains any meanings.
		 * 
		 * @return <tt>true</tt> if the meaning list is currently not empty
		 */
		boolean hasMeanings() {
			return !listModel.isEmpty();
		}

		/**
		 * Returns the meaning actions to perform based on the user input in the
		 * meaning area.
		 * 
		 * @return the meaning actions to perform
		 */
		List<DictObjectAction> getMeaningActions() {
			return new ArrayList<DictObjectAction>(meaningActions);
		}
	}

	/**
	 * The GUI components of the upper part of the entry dialog, containing
	 * orthography, pronunciation, and lesson text fields.
	 * 
	 * @author thrar
	 */
	private static class TextFieldArea {
		private final StringListEditor pronunciationEditor = new StringListEditor(
				"pronunciation");
		private final CustomTextField orthField = new CustomTextField(20);
		private final LabeledComboBox lessonBox = new LabeledComboBox(
				new SortedComboBoxModel());
		private final JVLTModel model;
		private JComponent guiComponent;

		TextFieldArea(JVLTModel model) {
			this.model = model;
		}

		/**
		 * Builds the text field area of the entry dialog.
		 * 
		 * @return the text field area of the entry dialog
		 */
		private JComponent buildTextFieldArea() {
			final JComponent textFieldPanel = new JPanel();
			textFieldPanel.setLayout(new GridBagLayout());

			pronunciationEditor
					.addComponentReplacementListener(new ComponentReplacementListener() {
						public void componentReplaced(
								ComponentReplacementEvent ev) {
							textFieldPanel.remove(ev.getOldComponent());
							CustomConstraints cc = new CustomConstraints();
							cc.update(0, 1, 1.0, 0.0, 2, 1);
							textFieldPanel.add(ev.getNewComponent(), cc);
							SwingUtilities.getWindowAncestor(textFieldPanel)
									.pack();
						}
					});
			Font font = ((UIConfig) JVLT.getConfig()).getFontProperty(
					"ui_pron_font");
			if (font != null) {
				pronunciationEditor.setFont(font);
			}

			orthField.setActionCommand("orthography");
			font = ((UIConfig) JVLT.getConfig()).getFontProperty(
					"ui_orth_font");
			if (font != null) {
				orthField.setFont(font);
			}

			lessonBox.setLabel("lesson");
			lessonBox.setEditable(true);

			CustomConstraints cc = new CustomConstraints();
			cc.update(0, 0, 0.0, 0.0);
			textFieldPanel.add(orthField.getLabel(), cc);
			cc.update(1, 0, 1.0, 0.0);
			textFieldPanel.add(orthField, cc);
			cc.update(0, 1, 1.0, 0.0, 2, 1);
			textFieldPanel.add(pronunciationEditor.getInputComponent(), cc);
			cc.update(0, 2, 0.0, 0.0, 1, 1);
			textFieldPanel.add(lessonBox.getLabel(), cc);
			cc.update(1, 2, 1.0, 0.0, 1, 1);
			textFieldPanel.add(lessonBox, cc);

			return textFieldPanel;
		}

		/**
		 * Returns the GUI component for this area, building it if necessary.
		 * 
		 * @return the GUI component for this area
		 */
		JComponent getGuiComponent() {
			if (guiComponent == null) {
				guiComponent = buildTextFieldArea();
			}
			return guiComponent;
		}

		/**
		 * Sets the currently selected entries, updating the fields as needed.
		 * 
		 * @param currentEntries the currently selected entries
		 */
		void setCurrentEntries(List<Entry> currentEntries) {
			updateComponents(currentEntries);
		}

		/**
		 * Updates display components in this area depending on the selected
		 * elements.
		 * 
		 * @param selectedEntries the currently selected entries
		 */
		private void updateComponents(List<Entry> currentEntries) {
			MetaData data = model.getDictModel().getMetaData(Entry.class);
			ChoiceAttribute attr = (ChoiceAttribute) data
					.getAttribute("Lesson");
			for (Object availableLesson : attr.getValues()) {
				lessonBox.addItem(availableLesson);
			}

			if (currentEntries.size() == 1) {
				orthField.setEnabled(true);
				orthField.setText(currentEntries.get(0).getOrthography());
				pronunciationEditor.setEnabled(true);
				pronunciationEditor.setSelectedItems(currentEntries.get(0)
						.getPronunciations());
				setSelectedLesson(currentEntries.get(0).getLesson(), true);

			} else {
				orthField.setEnabled(false);
				orthField.setText("");
				pronunciationEditor.setEnabled(false);
				pronunciationEditor.setSelectedItems(new String[0]);

				if (!currentEntries.isEmpty()) {
					// multiple entries - allow lesson if all have the same
					boolean lessonEnabled = true;
					String firstLesson = currentEntries.get(0).getLesson();
					for (Entry entry : currentEntries) {
						if (!firstLesson.equals(entry.getLesson())) {
							firstLesson = "";
							lessonEnabled = false;
							break;
						}
					}
					setSelectedLesson(firstLesson, lessonEnabled);
				} else {
					setSelectedLesson("", false);
				}

			}
		}

		/**
		 * Focuses the default component, i.e. the first field in the dialog.
		 */
		void setDefaultFocus() {
			orthField.requestFocusInWindow();
		}

		/**
		 * Returns the data currently entered in the orthography field.
		 * 
		 * @return the data currently entered in the orthography field
		 */
		String getSelectedOrthography() {
			return orthField.getText();
		}

		/**
		 * Returns the currently entered pronunciations.
		 * 
		 * @return the currently entered pronunciations
		 */
		List<String> getSelectedPronunciations() {
			return Utils.objectArrayToStringList(pronunciationEditor
					.getSelectedItems());
		}

		/**
		 * Sets the currently selected lesson and enables/disables the lesson
		 * combo box.
		 * 
		 * @param lesson the lesson to select, pass an empty string to select no
		 *            lesson
		 * @param enabled the new enabled status of the lesson combo box
		 */
		void setSelectedLesson(String lesson, boolean enabled) {
			lessonBox.setSelectedItem(lesson);
			lessonBox.setEnabled(enabled);
		}

		/**
		 * Returns the currently selected lesson, or an empty string if none is
		 * selected.
		 * 
		 * @return the currently selected lesson, or an empty string if none is
		 *         selected
		 */
		String getSelectedLesson() {
			return lessonBox.getSelectedItem().toString();
		}
	}
}
