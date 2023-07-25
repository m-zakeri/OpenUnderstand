package net.sourceforge.jvlt.ui;

import java.awt.Component;
import java.awt.Container;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.Graphics2D;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Toolkit;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.awt.print.PrinterException;
import java.awt.print.PrinterJob;
import java.beans.XMLDecoder;
import java.beans.XMLEncoder;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Locale;
import java.util.Set;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JEditorPane;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JToolBar;
import javax.swing.SwingUtilities;
import javax.swing.UIManager;
import javax.swing.WindowConstants;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import javax.swing.text.html.HTMLDocument;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.EditEntriesAction;
import net.sourceforge.jvlt.actions.EditEntryAction;
import net.sourceforge.jvlt.actions.LanguageChangeAction;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.event.FilterListener;
import net.sourceforge.jvlt.event.ModelResetEventListener;
import net.sourceforge.jvlt.event.SelectionListener;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.UndoableActionListener;
import net.sourceforge.jvlt.io.DictReaderException;
import net.sourceforge.jvlt.io.VersionException;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.multimedia.AudioFile;
import net.sourceforge.jvlt.multimedia.CustomMultimediaFile;
import net.sourceforge.jvlt.multimedia.ImageFile;
import net.sourceforge.jvlt.os.OSController;
import net.sourceforge.jvlt.query.ObjectQuery;
import net.sourceforge.jvlt.quiz.QuizInfo;
import net.sourceforge.jvlt.ui.components.CustomTabbedPane;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.BrowserDialog;
import net.sourceforge.jvlt.ui.dialogs.CustomDialog;
import net.sourceforge.jvlt.ui.dialogs.DictFileChooser;
import net.sourceforge.jvlt.ui.dialogs.ErrorLogDialog;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.dialogs.PrintPreviewDialog;
import net.sourceforge.jvlt.ui.dialogs.PropertiesDialogData;
import net.sourceforge.jvlt.ui.dialogs.ResetStatsDialogData;
import net.sourceforge.jvlt.ui.dialogs.SettingsDialogData;
import net.sourceforge.jvlt.ui.io.ExportDialog;
import net.sourceforge.jvlt.ui.io.ImportDialog;
import net.sourceforge.jvlt.ui.quiz.QuizModel;
import net.sourceforge.jvlt.ui.quiz.QuizPanel;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.ui.utils.TablePrinter;
import net.sourceforge.jvlt.ui.vocabulary.EntryPanel;
import net.sourceforge.jvlt.ui.vocabulary.EntrySelectionDialogData;
import net.sourceforge.jvlt.ui.vocabulary.ExamplePanel;
import net.sourceforge.jvlt.utils.ChoiceFormatter;
import net.sourceforge.jvlt.utils.Config;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.DetailedException;
import net.sourceforge.jvlt.utils.Utils;
import net.sourceforge.jvlt.utils.XSLTransformer;

import org.apache.log4j.Logger;
import org.apache.log4j.PropertyConfigurator;
import org.w3c.dom.Document;

public class JVLTUI implements ActionListener, UndoableActionListener,
		DictUpdateListener, SelectionListener, ModelResetEventListener {

	static {
		initStatic();
	}

	private static final Logger logger = Logger.getLogger(JVLTUI.class);

	private class ChangeHandler implements ChangeListener {
		public void stateChanged(ChangeEvent ev) {
			Component tab = _tab_pane.getSelectedComponent();
			if (tab == _quiz_tab.getWizard().getContent()) {
				JVLTUI.this._main_frame.getRootPane().setDefaultButton(
						_quiz_tab.getWizard().getDefaultButton());
			} else {
				JVLTUI.this._main_frame.getRootPane().setDefaultButton(null);
			}
		}
	}

	private class EntryFilterListener implements FilterListener<Entry> {
		public void filterApplied(FilterEvent<Entry> event) {
			_matched_entries = event.getMatchedItems();
			updateStatusBar();
		}
	}

	private class ExampleFilterListener implements FilterListener<Example> {
		public void filterApplied(FilterEvent<Example> event) {
			_matched_examples = event.getMatchedItems();
			updateStatusBar();
		}
	}

	private static final JVLTModel _model = new JVLTModel();
	
	private Dict _dict;
	private Collection<Entry> _matched_entries;
	private Collection<Example> _matched_examples;
	private final LinkedList<String> _recent_files;

	private EntryPanel _entry_tab;
	private ExamplePanel _example_tab;
	private QuizPanel _quiz_tab;
	private JFrame _main_frame;
	private CustomAction _clear_recent_files_action;
	private CustomAction _undo_action;
	private CustomAction _redo_action;
	private CustomAction _toolbar_redo_action;
	private CustomAction _toolbar_undo_action;
	private JLabel _left_status_label;
	private JMenu _recent_files_menu;
	private CustomTabbedPane _tab_pane;
	private ErrorLogDialog _error_dialog;
	private final boolean _is_mac;

	public static JVLTModel getModel() {
		return _model;
	}

	public JVLTUI(boolean is_on_mac) {
		_is_mac = is_on_mac;

		_matched_entries = null;
		_matched_examples = null;
		_recent_files = new LinkedList<String>();
		String[] file_names = JVLT.getConfig().getStringListProperty(
				"recent_files", new String[0]);
		for (String fileName : file_names) {
			_recent_files.add(fileName);
		}

		// Create empty dictionary. Will be replaced in method dictUpdated().
		_dict = new Dict();

		// Load runtime properties
		loadRuntimeProperties();

		// Handle new data versions
		String last_data_version = JVLT.getConfig().getProperty(
				"last_data_version", JVLT.getDataVersion());
		if (last_data_version.compareTo(JVLT.getDataVersion()) < 0) {
			handleNewDataVersion(last_data_version, JVLT.getDataVersion());
		}

		// Listen to model events
		_model.getDictModel().addUndoableActionListener(this);
		_model.getDictModel().addModelResetEventListener(this);
		_model.getDictModel().addDictUpdateListener(this);
		_model.getQueryModel().addUndoableActionListener(this);
		_model.getQueryModel().addModelResetEventListener(this);
		_model.getQueryModel().addDictUpdateListener(this);
	}

	public void run() {
		_main_frame.pack();
		_main_frame.setVisible(true);

		Config conf = JVLT.getConfig();
		if (conf.getBooleanProperty("restore_previously_open_file", false)) {
			String dict_file_name = conf.getProperty("dict_file");
			if (dict_file_name != null && !dict_file_name.equals("")) {
				load(dict_file_name);
			}
		}

		// If no default dictionary was specified or if loading it failed,
		// start with an empty one.
		if (_model.getDict() == null) {
			_model.newDict();
		}
	}

	public void actionPerformed(ActionEvent e) {
		String command = e.getActionCommand();
		if (command.equals("new") || command.equals("open")
				|| command.startsWith("open_")) {
			if (!finishQuiz()) {
				return;
			}

			// ----------
			// Ask whether changes should be saved.
			// ----------
			if (_model.isDataModified()) {
				int result = GUIUtils.showSaveDiscardCancelDialog(_main_frame,
						"save_changes");
				if (result == JOptionPane.YES_OPTION) {
					if (!save()) {
						return;
					}
				} else if (result == JOptionPane.CANCEL_OPTION) {
					return;
				}
				// Proceed if result is JOptionPane.NO_OPTION.
			}
		}

		if ("new".equals(command)) {
			_model.newDict();
		} else if ("open".equals(command)) {
			JFileChooser chooser = new DictFileChooser(_model.getDictFileName());
			int val = chooser.showOpenDialog(_main_frame);
			if (val == JFileChooser.APPROVE_OPTION) {
				String file_name = chooser.getSelectedFile().getPath();
				load(file_name);
			}
		} else if (command.startsWith("open_")) {
			int index = Integer.parseInt(command
					.substring(command.length() - 1));
			load(_recent_files.get(index));
		} else if ("clear_menu".equals(command)) {
			_recent_files.clear();
			updateRecentFilesMenu();
		} else if ("save".equals(command)) {
			save();
		} else if ("save_as".equals(command)) {
			saveAs();
		} else if ("print_file".equals(command)) {
			TablePrinter printer = getTablePrinter();
			print(printer);
		} else if ("print_preview".equals(command)) {
			TablePrinter printer = getTablePrinter();
			try {
				printer.renderPages((Graphics2D) _main_frame.getGraphics());
				PrintPreviewDialog dlg = new PrintPreviewDialog(_main_frame,
						I18nService.getString("Labels", "print_preview"), printer);
				dlg.pack();
				dlg.setVisible(true);
				if (dlg.getOption() == PrintPreviewDialog.PRINT_OPTION) {
					print(printer);
				}
			} catch (PrinterException ex) {
				MessageDialog.showDialog(_main_frame,
						MessageDialog.WARNING_MESSAGE, ex.getMessage());
			}
		} else if ("import".equals(command)) {
			ImportDialog dialog = new ImportDialog(_main_frame, _model);
			GUIUtils.showDialog(_main_frame, dialog);
		} else if ("export".equals(command)) {
			ExportDialog dialog = new ExportDialog(_main_frame, _model);
			GUIUtils.showDialog(_main_frame, dialog);
		} else if ("quit".equals(command)) {
			tryToQuit();
		} else if ("undo".equals(command)) {
			_model.undo();
		} else if ("redo".equals(command)) {
			_model.redo();
		} else if ("dict_properties".equals(command)) {
			if (!finishQuiz()) {
				return;
			}

			PropertiesDialogData ddata = new PropertiesDialogData(_dict
					.getLanguage());
			CustomDialog dlg = new CustomDialog(ddata, _main_frame, I18nService
					.getString("Labels", "dict_properties"));
			GUIUtils.showDialog(_main_frame, dlg);
			if (dlg.getStatus() == AbstractDialog.OK_OPTION) {
				LanguageChangeAction lca = new LanguageChangeAction(_dict
						.getLanguage(), ddata.getLanguage());
				lca
						.setMessage(I18nService.getString("Actions",
								"change_language"));
				_model.getDictModel().executeAction(lca);
			}
		} else if ("reset_stats".equals(command)) {
			resetStats();
		} else if ("error_log".equals(command)) {
			GUIUtils.showDialog(_main_frame, _error_dialog);
		} else if ("settings".equals(command)) {
			showSettings();
		} else if ("help".equals(command)) {
			Locale locale = Locale.getDefault();
			URL url = JVLTUI.class.getResource("/doc/" + locale.toString()
					+ "/doc.html");
			if (url == null) {
				url = JVLTUI.class.getResource("/doc/default/doc.html");
			}

			BrowserDialog dlg = new BrowserDialog(_main_frame, url);
			GUIUtils.showDialog(_main_frame, dlg);
		} else if ("about".equals(command)) {
			showAbout();
		}
	}

	public void actionPerformed(UndoableActionEvent event) {
		updateMenu();
		updateTitle();
	}

	public void modelResetted(ModelResetEvent event) {
		if (event.getType() == ModelResetEvent.RESET_ALL) {
			updateMenu();
		}

		updateTitle();
	}

	public synchronized void dictUpdated(DictUpdateEvent e) {
		if (e instanceof NewDictDictUpdateEvent) {
			_dict = ((NewDictDictUpdateEvent) e).getDict();
			updateMenu();
			updateTitle();
		}
	}

	public void objectSelected(SelectionEvent e) {
		Object obj = e.getElement();
		if (obj instanceof Example) {
			_tab_pane.setSelectedComponent(_example_tab);
		} else if (obj instanceof Entry || obj instanceof Sense) {
			_tab_pane.setSelectedComponent(_entry_tab);
		} else if (obj instanceof AudioFile) {
			AudioFile file = (AudioFile) obj;
			try {
				file.play();
			} catch (IOException ex) {
				String msg = I18nService.getString("Messages", "loading_failed");
				MessageDialog.showDialog(_main_frame,
						MessageDialog.ERROR_MESSAGE, msg, ex.getMessage());
			}
		} else if (obj instanceof ImageFile) {
			ImageFile file = (ImageFile) obj;
			try {
				file.show(_main_frame);
			} catch (IOException ex) {
				String msg = I18nService.getString("Messages", "loading_failed");
				MessageDialog.showDialog(_main_frame,
						MessageDialog.ERROR_MESSAGE, msg, ex.getMessage());
			}
		} else if (obj instanceof CustomMultimediaFile) {
			CustomMultimediaFile cmf = (CustomMultimediaFile) obj;
			try {
				cmf.play();
			} catch (IOException ex) {
				String msg = I18nService.getString("Messages", "loading_failed");
				MessageDialog.showDialog(_main_frame,
						MessageDialog.ERROR_MESSAGE, msg, ex.getMessage());
			}
		}
	}

	private void initUI() {
		_main_frame = new JFrame();
		_main_frame
				.setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);
		_main_frame.addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosing(WindowEvent e) {
				tryToQuit();
			}
		});
		URL url = JVLTUI.class.getResource("/images/jvlt.png");
		_main_frame.setIconImage(Toolkit.getDefaultToolkit().getImage(url));

		// Toolbar actions
		_toolbar_undo_action = GUIUtils.createIconAction(this, "undo");
		_toolbar_redo_action = GUIUtils.createIconAction(this, "redo");
		CustomAction toolbar_new_action = GUIUtils
				.createIconAction(this, "new");
		CustomAction toolbar_open_action = GUIUtils.createIconAction(this,
				"open");
		CustomAction toolbar_save_action = GUIUtils.createIconAction(this,
				"save");

		// File menu
		CustomAction new_action = GUIUtils.createTextAction(this, "new");
		CustomAction open_action = GUIUtils.createTextAction(this, "open");
		CustomAction open_recent_action = GUIUtils.createTextAction(this,
				"open_recent");
		_clear_recent_files_action = GUIUtils.createTextAction(this,
				"clear_menu");
		CustomAction save_action = GUIUtils.createTextAction(this, "save");
		CustomAction save_as_action = GUIUtils
				.createTextAction(this, "save_as");
		CustomAction print_preview_action = GUIUtils.createTextAction(this,
				"print_preview");
		CustomAction print_action = GUIUtils.createTextAction(this,
				"print_file");
		CustomAction import_action = GUIUtils.createTextAction(this, "import");
		CustomAction export_action = GUIUtils.createTextAction(this, "export");
		CustomAction quit_action = GUIUtils.createTextAction(this, "quit");

		// Edit menu
		_undo_action = GUIUtils.createTextAction(this, "undo");
		_undo_action.putValue(Action.NAME, I18nService.getString("Actions",
				"undo", new Object[] { "" }).replaceAll("\\$", ""));
		_undo_action.setEnabled(false);
		_redo_action = GUIUtils.createTextAction(this, "redo");
		_redo_action.putValue(Action.NAME, I18nService.getString("Actions",
				"redo", new Object[] { "" }).replaceAll("\\$", ""));
		_undo_action.setEnabled(false);
		CustomAction properties_action = GUIUtils.createTextAction(this,
				"dict_properties");

		// Tools menu
		CustomAction reset_stats_action = GUIUtils.createTextAction(this,
				"reset_stats");
		CustomAction error_log_action = GUIUtils.createTextAction(this,
				"error_log");
		CustomAction settings_action = GUIUtils.createTextAction(this,
				"settings");

		// Help menu
		CustomAction help_action = GUIUtils.createTextAction(this, "help");
		CustomAction about_action = GUIUtils.createTextAction(this, "about");

		JMenuItem item;
		JMenuBar menu_bar = new JMenuBar();
		JMenu file_menu = GUIUtils.createMenu("menu_file");
		menu_bar.add(file_menu);
		item = new JMenuItem(new_action);
		item.setIcon(null);
		file_menu.add(item);
		item = new JMenuItem(open_action);
		item.setIcon(null);
		file_menu.add(item);
		_recent_files_menu = new JMenu(open_recent_action);
		_recent_files_menu.addSeparator();
		_recent_files_menu.add(new JMenuItem(_clear_recent_files_action));
		file_menu.add(_recent_files_menu);
		file_menu.addSeparator();
		item = new JMenuItem(save_action);
		item.setIcon(null);
		file_menu.add(item);
		file_menu.add(save_as_action);
		file_menu.addSeparator();
		file_menu.add(print_action);
		file_menu.add(print_preview_action);
		file_menu.addSeparator();
		file_menu.add(import_action);
		file_menu.add(export_action);
		if (!_is_mac) {
			file_menu.addSeparator();
			file_menu.add(quit_action);
		}

		JMenu edit_menu = GUIUtils.createMenu("menu_edit");
		menu_bar.add(edit_menu);
		edit_menu.add(_undo_action);
		edit_menu.add(_redo_action);
		edit_menu.addSeparator();
		edit_menu.add(properties_action);
		JMenu tools_menu = GUIUtils.createMenu("menu_tools");
		menu_bar.add(tools_menu);
		tools_menu.add(reset_stats_action);
		tools_menu.add(error_log_action);

		if (!_is_mac) {
			tools_menu.addSeparator();
			tools_menu.add(settings_action);
		}

		JMenu help_menu = GUIUtils.createMenu("menu_help");
		menu_bar.add(help_menu);
		help_menu.add(help_action);
		if (!_is_mac) {
			help_menu.add(about_action);
		}

		_main_frame.setJMenuBar(menu_bar);

		SelectionNotifier notifier = new SelectionNotifier();
		notifier.addSelectionListener(this);
		_example_tab = new ExamplePanel(_model, notifier);
		_example_tab.loadState((UIConfig) JVLT.getConfig());
		_example_tab.addFilterListener(new ExampleFilterListener());
		_entry_tab = new EntryPanel(_model, notifier);
		_entry_tab.loadState((UIConfig) JVLT.getConfig());
		_entry_tab.addFilterListener(new EntryFilterListener());
		_quiz_tab = new QuizPanel(_model, notifier);

		_tab_pane = new CustomTabbedPane();
		_tab_pane.addTab("vocabulary", _entry_tab);
		_tab_pane.addTab("examples", _example_tab);
		_tab_pane.addTab("quiz", _quiz_tab);
		_tab_pane.addChangeListener(new ChangeHandler());

		// ----------
		// Create status bar
		// ----------
		JPanel status_bar = new JPanel();
		_left_status_label = new JLabel("");
		status_bar.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		status_bar.add(_left_status_label, cc);
		cc.update(1, 0, 1.0, 0.0);
		status_bar.add(Box.createHorizontalGlue(), cc);

		// ----------
		// Create tool bar.
		// ----------
		JToolBar tool_bar = new JToolBar();
		tool_bar.add(toolbar_new_action);
		tool_bar.add(toolbar_open_action);
		tool_bar.add(toolbar_save_action);
		tool_bar.add(_toolbar_undo_action);
		tool_bar.add(_toolbar_redo_action);
		tool_bar.setFloatable(false);
		tool_bar.add(Box.createHorizontalGlue());

		Container cpane = _main_frame.getContentPane();
		cpane.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		cpane.add(tool_bar, cc);
		cc.update(0, 1, 1.0, 1.0);
		cpane.add(_tab_pane, cc);
		cc.update(0, 2, 1.0, 0.0);
		cpane.add(status_bar, cc);
		
		//-----------
		// Restore previous size
		//-----------
		cpane.setPreferredSize(
				((UIConfig) JVLT.getConfig()).getDimensionProperty(
						"MainFrame.size", new Dimension(720, 590)));

		// ----------
		// Init data.
		// ----------
		updateStatusBar();
		if (_recent_files.size() > 0) {
			setMostRecentFile(_recent_files.get(0));
		} else {
			updateRecentFilesMenu();
		}

		// ----------
		// Dialogs
		// ----------
		_error_dialog = new ErrorLogDialog(_main_frame);
	}

	private void showError(String short_message, String long_message) {
		MessageDialog.showDialog(_main_frame, MessageDialog.ERROR_MESSAGE,
				short_message, long_message);
	}

	private boolean saveAs() {
		String file_name = DictFileChooser.selectSaveFile(_model
				.getDictFileName(), DictFileChooser.FileType.JVLT_FILES,
				_main_frame);
		if (file_name == null) {
			return false;
		}

		/* Show dialog if the file already exists */
		boolean write_file = true;
		if (new File(file_name).exists()) {
			if (JOptionPane.showConfirmDialog(_main_frame, I18nService.getString(
					"Messages", "overwrite"), I18nService.getString("Labels",
					"confirm"), JOptionPane.YES_NO_OPTION) != JOptionPane.YES_OPTION) {
				write_file = false;
			}
		}

		if (write_file) {
			try {
				_model.save(file_name);
				updateTitle();
				setMostRecentFile(file_name);

				return true;
			} catch (DetailedException ex) {
				ex.printStackTrace();
				showError(ex.getShortMessage(), ex.getLongMessage());
			}
		}

		return false;
	}

	private boolean save() {
		if (_model.getDictFileName() == null) {
			return saveAs();
		}

		try {
			_model.save();
			setMostRecentFile(_model.getDictFileName());
			return true;
		} catch (DetailedException ex) {
			showError(ex.getShortMessage(), ex.getLongMessage());
			return false;
		}
	}

	private void print(TablePrinter printer) {
		final PrinterJob job = PrinterJob.getPrinterJob();
		job.setPrintable(printer);
		if (!job.printDialog()) {
			return;
		}
		final MessageDialog dlg = new MessageDialog(_main_frame,
				MessageDialog.INFO_MESSAGE, I18nService.getString("Messages",
						"printing"), null);

		Runnable show_dlg = new Runnable() {
			public void run() {
				GUIUtils.showDialog(_main_frame, dlg);
			}
		};
		final Runnable hide_dlg = new Runnable() {
			public void run() {
				dlg.setVisible(false);
			}
		};
		Runnable print = new Runnable() {
			public void run() {
				try {
					job.print();
				} catch (PrinterException ex) {
					ex.printStackTrace();
				}
				SwingUtilities.invokeLater(hide_dlg);
			}
		};

		SwingUtilities.invokeLater(show_dlg);
		Thread thread = new Thread(print);
		thread.start();
	}

	private void load(String dict_file_name) {
		final String file_name = dict_file_name;
		Runnable load_data = new Runnable() {
			public void run() {
				try {
					_model.load(file_name);
					setMostRecentFile(file_name);
				} catch (DictReaderException e) {
					Exception ex = e.getException();
					if (ex != null && ex instanceof VersionException) {
						VersionException ve = (VersionException) ex;
						if (ve.getVersion().compareTo(JVLT.getDataVersion()) > 0) {
							handleLoadException(ve, file_name);
						} else {
							String text = I18nService.getString("Messages",
									"convert_file");
							int result = MessageDialog.showDialog(_main_frame,
									MessageDialog.WARNING_MESSAGE,
									MessageDialog.OK_CANCEL_OPTION, text);
							if (result == MessageDialog.OK_OPTION) {
								loadVersion(file_name, ve.getVersion());
							}
						}
					} else {
						handleLoadException(e, file_name);
					}
				} catch (Exception ex) {
					handleLoadException(ex, file_name);
				}
			}
		};

		Thread thread = new Thread(load_data);
		thread.start();
	}

	private void loadVersion(String file, String version) {
		try {
			_model.load(file, version);
			DictUpdater updater = new DictUpdater(version);
			updater.updateDict(_model.getDict());
			setMostRecentFile(file);
		} catch (Exception dre) {
			handleLoadException(dre, file);
		}
	}

	private void handleLoadException(Exception ex, String file_name) {
		String long_message = null;
		String short_message = null;
		if (ex instanceof DictReaderException) {
			DictReaderException dre = (DictReaderException) ex;
			short_message = dre.getShortMessage();
			long_message = dre.getLongMessage();
		} else if (ex instanceof IOException) {
			IOException ioe = (IOException) ex;
			short_message = I18nService.getString("Messages", "loading_failed");
			long_message = ioe.getMessage();
		} else if (ex instanceof VersionException) {
			VersionException ve = (VersionException) ex;
			short_message = I18nService.getString("Messages", "version_too_large");
			long_message = ve.getMessage();
		} else {
			ex.printStackTrace();
			short_message = I18nService.getString("Messages", "unknown_error");
			long_message = ex.getMessage();
		}

		if (_recent_files.contains(file_name)) {
			int result = OpenErrorDialog.showDialog(_main_frame, short_message,
					long_message);
			if (result == OpenErrorDialog.REMOVE_OPTION) {
				_recent_files.remove(file_name);
				updateRecentFilesMenu();
			}
		} else {
			showError(short_message, long_message);
		}
	}

	private void tryToQuit() {
		if (requestQuit()) {
			exit();
		}
		// Else cancel.
	}

	/**
	 * Tests whether the application can safely be terminated. If there is
	 * modified data a dialog is shown. This method is public as it can be
	 * called by {@link OSController}.
	 * 
	 * @return Whether it is safe to quit the application
	 */
	public boolean requestQuit() {
		if (!finishQuiz()) {
			return false;
		}

		if (!_model.isDataModified()) {
			return true;
		}
		int result = GUIUtils.showSaveDiscardCancelDialog(_main_frame,
				"save_changes");
		if (result == JOptionPane.YES_OPTION) {
			if (save()) {
				return true;
			}
		} else if (result == JOptionPane.NO_OPTION) {
			return true;
		}

		return false;
	}

	/**
	 * Shows the about dialog. This method is public as it can be called by
	 * {@link OSController}.
	 */
	public void showAbout() {
		AboutDialog dlg = new AboutDialog(_main_frame);
		GUIUtils.showDialog(_main_frame, dlg);
	}

	/**
	 * Shows the settings dialog. This method is public as it can be called by
	 * {@link OSController}.
	 */
	public void showSettings() {
		SettingsDialogData ddata = new SettingsDialogData(_model);
		CustomDialog dlg = new CustomDialog(ddata, _main_frame, I18nService
				.getString("Labels", "settings"));
		GUIUtils.showDialog(_main_frame, dlg);
	}

	/**
	 * Checks whether there is an unfinished quiz and - if yes - asks the user
	 * whether to save or discard the quiz results, or to cancel.
	 * 
	 * @return false if the user selects "Cancel", and true otherwise.
	 */
	private boolean finishQuiz() {
		QuizModel model = (QuizModel) _quiz_tab.getWizard().getModel();
		if (model.existsUnfinishedQuiz()) {
			int result = GUIUtils.showSaveDiscardCancelDialog(_main_frame,
					"save_quiz");
			if (result == JOptionPane.YES_OPTION) {
				model.saveQuizResults();
			}

			return result == JOptionPane.YES_OPTION
					|| result == JOptionPane.NO_OPTION;
		}
		return true;
	}

	/**
	 * Prepare for quit
	 * 
	 * This function save the last state of the config, examples, etc.
	 */
	public void prepareForQuit() {
		UIConfig conf = (UIConfig) JVLT.getConfig();

		// -----
		// Save dictionary file name
		// -----
		String dict_file_name = _model.getDictFileName();
		if (dict_file_name == null) {
			conf.setProperty("dict_file", "");
		} else {
			conf.setProperty("dict_file", dict_file_name);
		}

		// -----
		// Save list of recent files
		// -----
		conf.setProperty("recent_files", _recent_files.toArray(new String[0]));

		// -----
		// Save table columns.
		// -----
		_entry_tab.saveState(conf);
		_example_tab.saveState(conf);

		// Save runtime properties
		saveRuntimeProperties();

		// Save current data version
		conf.setProperty("last_data_version", JVLT.getDataVersion());
		
		// Save main frame size
		conf.setProperty("MainFrame.size", _main_frame.getContentPane()
				.getSize());
		
		// Save defaults for settings that cannot be configured
		// via the settings dialog
		if (!conf.containsKey("Table.showTooltips"))
			conf.setProperty("Table.showTooltips", true);
		if (!conf.containsKey("entry_table_arrow_direction_reversed"))
			conf.setProperty("entry_table_arrow_direction_reversed", false);

		try {
			JVLT.getConfig().store();
		} catch (IOException ex) {
			logger.error("Failed to save configuration", ex);
		}
	}

	private void exit() {
		prepareForQuit();
		System.exit(0);
	}

	private void resetStats() {
		ResetStatsDialogData data = new ResetStatsDialogData(_dict
				.getEntryCount(), _matched_entries.size());
		int result = CustomDialog.showDialog(data, _main_frame, I18nService
				.getString("Labels", "reset_stats"));
		if (result == AbstractDialog.OK_OPTION) {
			Collection<Entry> entries;
			if (data.resetAllEntries()) {
				entries = _dict.getEntries();
			} else {
				entries = _matched_entries;
			}

			if (entries.size() == 0) {
				return;
			}

			ArrayList<EditEntryAction> actions = new ArrayList<EditEntryAction>();
			for (Entry orig : entries) {
				Entry modified = (Entry) orig.clone();
				modified.resetStats();
				actions.add(new EditEntryAction(orig, modified));
			}
			EditEntriesAction action = new EditEntriesAction(actions
					.toArray(new EditEntryAction[0]));
			action.setMessage(I18nService.getString("Actions", "edit_entries",
					new Object[] { entries.size() }));
			_model.getDictModel().executeAction(action);
		}
	}

	private TablePrinter getTablePrinter() {
		TablePrinter printer = new TablePrinter();
		printer.setDataModel(_entry_tab.getTableModel());

		// Set column widths
		Config conf = JVLT.getConfig();
		_entry_tab.saveState((UIConfig) conf);
		double[] col_widths = conf.getNumberListProperty("column_widths",
				new double[0]);
		double total_width = 0.0;
		for (double colWidth : col_widths) {
			total_width += colWidth;
		}
		for (int i = 0; i < col_widths.length; i++) {
			printer.setColWidth(i, (int) (100 * col_widths[i] / total_width));
		}

		return printer;
	}

	private void updateStatusBar() {
		int total_entries = _dict.getEntryCount();
		int total_examples = _dict.getExampleCount();
		int shown_entries, shown_examples;
		if (_matched_entries == null) {
			shown_entries = total_entries;
		} else {
			shown_entries = _matched_entries.size();
		}
		if (_matched_examples == null) {
			shown_examples = total_examples;
		} else {
			shown_examples = _matched_examples.size();
		}

		ChoiceFormatter formatter = new ChoiceFormatter(I18nService.getString(
				"Labels", "num_words"));
		String entries_string = formatter.format(shown_entries);
		formatter.applyPattern(I18nService.getString("Labels", "num_examples"));
		String examples_string = formatter.format(shown_examples);
		String text = I18nService.getString("Labels", "words_examples",
				new Object[] { entries_string, examples_string, total_entries,
						total_examples });
		_left_status_label.setText(text);
	}

	private void updateMenu() {
		// ---------
		// Change undo menu item.
		if (_model.getNumUndoableActions() == 0) {
			String str = I18nService.getString("Actions", "undo",
					new Object[] { "" }).replaceAll("\\$", "");
			_undo_action.putValue(Action.NAME, str);
			_toolbar_undo_action.putValue(Action.SHORT_DESCRIPTION, str);
			_undo_action.setEnabled(false);
			_toolbar_undo_action.setEnabled(false);
		} else {
			String text = I18nService
					.getString("Actions", "undo", new Object[] { _model
							.getFirstUndoableAction().getMessage() });
			text = text.replaceAll("\\$", "");
			_undo_action.putValue(Action.NAME, text);
			_toolbar_undo_action.putValue(Action.SHORT_DESCRIPTION, text);
			_undo_action.setEnabled(true);
			_toolbar_undo_action.setEnabled(true);
		}

		// ---------
		// Change redo menu item.
		if (_model.getNumRedoableActions() == 0) {
			String str = I18nService.getString("Actions", "redo",
					new Object[] { "" }).replaceAll("\\$", "");
			_redo_action.putValue(Action.NAME, str);
			_toolbar_redo_action.putValue(Action.SHORT_DESCRIPTION, str);
			_redo_action.setEnabled(false);
			_toolbar_redo_action.setEnabled(false);
		} else {
			String text = I18nService
					.getString("Actions", "redo", new Object[] { _model
							.getFirstRedoableAction().getMessage() });
			text = text.replaceAll("\\$", "");
			_redo_action.putValue(Action.NAME, text);
			_toolbar_redo_action.putValue(Action.SHORT_DESCRIPTION, text);
			_redo_action.setEnabled(true);
			_toolbar_redo_action.setEnabled(true);
		}
	}

	private void updateTitle() {
		String title;
		String file_name = _model.getDictFileName();
		if (file_name == null) {
			title = I18nService.getString("Labels", "untitled");
		} else {
			int index = file_name.lastIndexOf(File.separatorChar);
			if (index > 0) {
				title = file_name.substring(index + 1, file_name.length());
			} else {
				title = file_name;
			}
		}

		if (_model.getDictModel().isDataModified()
				|| _model.getQueryModel().isDataModified()) {
			title += " (" + I18nService.getString("Labels", "modified") + ")";
		}

		title += " - jVLT";
		_main_frame.setTitle(title);
	}

	private void setMostRecentFile(String file_name) {
		_recent_files.remove(file_name);
		_recent_files.addFirst(file_name);
		while (_recent_files.size() > 5) {
			_recent_files.removeLast();
		}

		updateRecentFilesMenu();
	}

	private void updateRecentFilesMenu() {
		while (_recent_files_menu.getItemCount() > 2) {
			_recent_files_menu.remove(0);
		}
		Iterator<String> it = _recent_files.iterator();
		int index = 0;
		while (it.hasNext()) {
			File f = new File(it.next());
			CustomAction action = new CustomAction("open_" + index);
			action.addActionListener(this);
			action.putValue(Action.NAME, f.getName());
			_recent_files_menu.add(new JMenuItem(action), _recent_files_menu
					.getItemCount() - 2);
			index++;
		}

		_clear_recent_files_action.setEnabled(!_recent_files.isEmpty());
	}

	private void loadRuntimeProperties() {
		UIConfig conf = (UIConfig) JVLT.getConfig();
		String home = conf.getConfigDir() + File.separator;
		XMLDecoder decoder;

		try {
			// -----
			// Load and check filters
			// -----
			decoder = new XMLDecoder(new BufferedInputStream(
					new FileInputStream(home + "filters.xml")));
			ObjectQuery[] oqs = (ObjectQuery[]) decoder.readObject();

			if (oqs == null) {
				throw new IOException("Invalid filter list (null)");
			}

			for (int i = 0; i < oqs.length; i++) {
				if (oqs[i] == null) {
					throw new IOException("Invalid filter item (null)");
				} else if (!oqs[i].isValid()) {
					throw new IOException("Invalid filter item (invalid data)");
				}
			}
			JVLT.getRuntimeProperties().put("filters", oqs);
		} catch (Exception e) {
			// e.printStackTrace();
			JVLT.getRuntimeProperties().put("filter", new ObjectQuery[0]);
		}

		try {
			// -----
			// Load quiz entry filter
			// -----
			decoder = new XMLDecoder(new BufferedInputStream(
					new FileInputStream(home + "quizfilters.xml")));
			EntrySelectionDialogData.State[] states = (EntrySelectionDialogData.State[]) decoder
					.readObject();
			JVLT.getRuntimeProperties().put("quiz_entry_filters", states);
		} catch (Exception e) {
			// e.printStackTrace();
			JVLT.getRuntimeProperties().put("quiz_entry_filters", null);
		}

		try {
			// -----
			// Load quiz types
			// -----
			decoder = new XMLDecoder(new BufferedInputStream(
					new FileInputStream(home + "quiztypes.xml")));
			QuizInfo[] qinfos = (QuizInfo[]) decoder.readObject();
			decoder.close();
			JVLT.getRuntimeProperties().put("quiz_types", qinfos);
			JVLT.getRuntimeProperties().put("selected_quiz_type",
					conf.getProperty("selected_quiz_type", ""));
		} catch (Exception e) {
			// e.printStackTrace();
			JVLT.getRuntimeProperties().put("quiz_types", new QuizInfo[0]);
			JVLT.getRuntimeProperties().put("selected_quiz_type", "");
		}
	}

	private void saveRuntimeProperties() {
		UIConfig conf = (UIConfig) JVLT.getConfig();
		String home = conf.getConfigDir() + File.separator;
		XMLEncoder encoder;

		try {
			// -----
			// Save filters
			// -----
			ObjectQuery[] oqs = (ObjectQuery[]) JVLT.getRuntimeProperties()
					.get("filters");
			encoder = new XMLEncoder(new BufferedOutputStream(
					new FileOutputStream(home + "filters.xml")));
			encoder.writeObject(oqs);
			encoder.close();

			// -----
			// Save quiz entry filter
			// -----
			EntrySelectionDialogData.State[] states = (EntrySelectionDialogData.State[]) JVLT
					.getRuntimeProperties().get("quiz_entry_filters");
			encoder = new XMLEncoder(new BufferedOutputStream(
					new FileOutputStream(home + "quizfilters.xml")));
			encoder.writeObject(states);
			encoder.close();

			// -----
			// Save quiz types
			// -----
			QuizInfo[] qts = (QuizInfo[]) JVLT.getRuntimeProperties().get(
					"quiz_types");
			encoder = new XMLEncoder(new BufferedOutputStream(
					new FileOutputStream(home + "quiztypes.xml")));
			encoder.writeObject(qts);
			encoder.close();
			Object obj = JVLT.getRuntimeProperties().get("selected_quiz_type");
			if (obj == null) {
				conf.setProperty("selected_quiz_type", "");
			} else {
				conf.setProperty("selected_quiz_type", obj.toString());
			}

			// -----
			// Save language-specific settings
			// -----
			String lang = _dict.getLanguage();
			Object[] displayed_attributes = (Object[]) JVLT
					.getRuntimeProperties().get("displayed_attributes");
			String key = (lang == null || lang.equals("")) ? "displayed_attributes"
					: ("displayed_attributes_" + lang);
			JVLT.getConfig().setProperty(key, displayed_attributes);
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
	}

	private void handleNewDataVersion(String last_version,
			String current_version) {
		if (last_version.compareTo(current_version) >= 0) {
			return;
		}

		if (current_version.equals("1.2.1")) {
			// Add new attribute "CustomFields" to displayed_attributes_*
			// settings
			Config config = JVLT.getConfig();
			for (String key : config.getKeys()) {
				if (key.startsWith("displayed_attributes")) {
					Set<String> attrs = new HashSet<String>();
					attrs.addAll(Arrays.asList(config
							.getStringListProperty(key)));
					attrs.add("CustomFields");
					config.setProperty(key, attrs.toArray());
				}
			}
		}
	}

	public static void main(String[] args) {
		boolean is_on_mac = false;
		OSController controller = null;
		UIConfig config = new UIConfig();
		
		// Initialize global handle
		JVLT.init(config);
		
		String os_name = System.getProperty("os.name").toLowerCase();
		if (os_name.startsWith("mac os x")
				&& System.getProperty("mrj.version") != null) {
			try {
				@SuppressWarnings("unchecked")
				Class ControllerClass = Class
						.forName("net.sourceforge.jvlt.os.MacOSController");
				controller = (OSController) ControllerClass.newInstance();

				is_on_mac = true;

				System.setProperty("apple.laf.useScreenMenuBar", "true");
				System.setProperty(
						"com.apple.mrj.application.apple.menu.about.name",
						"jVLT");
			} catch (Exception ex) {
				logger.error("Could not load class \""
						+ "net.sourceforge.jvlt.os.MacOSController\"");
			}
		}

		// Set fonts.
		Font font = config.getFontProperty("ui_font");
		if (font != null) {
			String font_str = Utils.fontToString(font);
			System.getProperties()
					.put("swing.plaf.metal.controlFont", font_str);
			System.getProperties().put("swing.plaf.metal.menuFont", font_str);
			System.getProperties().put("swing.plaf.metal.systemFont", font_str);
			System.getProperties().put("swing.plaf.metal.userFont", font_str);
		}

		// Set look & feel.
		try {
			if (config.containsKey("look_and_feel")) {
				UIManager.setLookAndFeel(config.getProperty("look_and_feel"));
			} else {
				UIManager.setLookAndFeel(UIManager
						.getSystemLookAndFeelClassName());
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
		
		// Set locale
		Locale loc = Locale.getDefault();
		Locale.setDefault(config.getLocaleProperty("locale", loc));

		final JVLTUI ui = new JVLTUI(is_on_mac);
		if (controller != null) {
			controller.setMainView(ui);
		}

		SwingUtilities.invokeLater(new Runnable() {
			public void run() {
				ui.initUI();
				ui.run();
			}
		});
	}

	/**
	 * Initializes some static configuration, e.g. the logger.
	 */
	static void initStatic() {
		PropertyConfigurator.configure(JVLTUI.class
				.getResource("/log4j.properties"));
		System.setErr(new AppendingErrorStream());
	}

	/**
	 * A stream that proxies the previous System.err and additionally logs any
	 * printed Strings to a logger.
	 * 
	 * @author thrar
	 */
	private static class AppendingErrorStream extends PrintStream {
		private static final Logger logger = Logger
				.getLogger(AppendingErrorStream.class);

		/**
		 * Creates a new instance to proxy System.err.
		 */
		public AppendingErrorStream() {
			super(System.err);
		}

		@Override
		public void print(String s) {
			// print all Strings to the logger as well
			super.print(s);
			logger.error(s);
		}
	}
}

class DictUpdater {
	private final String _original_version;

	public DictUpdater(String original_version) {
		_original_version = original_version;
	}

	public void updateDict(Dict dict) {
		if (_original_version.compareTo("1.0") < 0) {
			for (Example ex : dict.getExamples()) {
				String id = ex.getID().replace('e', 'x');
				ex.setID(id);
			}
		}
	}
}

class AboutDialog extends JDialog {
	class ActionEventHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("close")) {
				setVisible(false);
			}
		}
	}

	private static final long serialVersionUID = 1L;

	public AboutDialog(Frame parent) {
		super(parent, I18nService.getString("Labels", "about"), true);
		init();
	}

	private void init() {
		Action close_action = GUIUtils.createTextAction(
				new ActionEventHandler(), "close");

		JEditorPane _html_pane = new JEditorPane();
		_html_pane.setEditable(false);
		_html_pane.setContentType("text/html");
		JScrollPane scrpane = new JScrollPane(_html_pane);
		scrpane.setPreferredSize(new Dimension(500, 400));

		getContentPane().setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		getContentPane().add(scrpane, cc);
		cc.update(0, 1, 0.0, 0.0);
		cc.fill = GridBagConstraints.NONE;
		getContentPane().add(new JButton(close_action), cc);

		InputStream xsl = AboutDialog.class
				.getResourceAsStream("/xml/info.xsl");
		XSLTransformer transformer = new XSLTransformer(xsl);
		try {
			InputStream xml = AboutDialog.class
					.getResourceAsStream("/xml/info.xml");
			DocumentBuilderFactory fac = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = fac.newDocumentBuilder();
			Document doc = builder.parse(xml);
			String html = transformer.transform(doc);
			_html_pane.setText(html);
			// System.out.println(html);

			URL url = AboutDialog.class.getResource("/doc/default/jvlt.png");
			HTMLDocument htmldoc = (HTMLDocument) _html_pane.getDocument();
			htmldoc.setBase(Utils.getDirectory(url));

			_html_pane.setCaretPosition(0);
		} catch (Exception ex) {
			ex.printStackTrace();
		}
	}
}

class OpenErrorDialog extends MessageDialog {
	private static final long serialVersionUID = 1L;

	public static final int REMOVE_OPTION = USER_OPTION;

	public static int showDialog(Frame parent, String message, String details) {
		_dialog = new OpenErrorDialog(parent, message, details);
		GUIUtils.showDialog(parent, _dialog);
		return _dialog.getResult();
	}

	private JButton _remove_recent_button;

	@Override
	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("remove_recent")) {
			_result = REMOVE_OPTION;
			setVisible(false);
		} else {
			super.actionPerformed(ev);
		}
	}

	@Override
	protected void initUI() {
		Action remove_recent_action = GUIUtils.createTextAction(this,
				"remove_recent");
		_remove_recent_button = new JButton(remove_recent_action);

		super.initUI();
	}

	@Override
	protected void updateButtonRow() {
		CustomConstraints cc = new CustomConstraints();
		_button_panel.remove(_ok_button);
		_button_panel.remove(_remove_recent_button);
		_button_panel.remove(_details_button);
		cc.update(1, 0, 0.0, 0.0);
		_button_panel.add(_ok_button, cc);
		cc.update(2, 0, 0.0, 0.0);
		_button_panel.add(_remove_recent_button, cc);
		cc.update(3, 0, 0.0, 0.0);
		_button_panel.add(_details_button, cc);
	}

	private OpenErrorDialog(Frame parent, String message, String details) {
		super(parent, ERROR_MESSAGE, message, details);
	}
}
