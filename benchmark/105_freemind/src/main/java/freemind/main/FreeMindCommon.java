/*FreeMind - A Program for creating and viewing Mindmaps
 *Copyright (C) 2000-2006  Joerg Mueller, Daniel Polansky, Christian Foltin and others.
 *
 *See COPYING for Details
 *
 *This program is free software; you can redistribute it and/or
 *modify it under the terms of the GNU General Public License
 *as published by the Free Software Foundation; either version 2
 *of the License, or (at your option) any later version.
 *
 *This program is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *GNU General Public License for more details.
 *
 *You should have received a copy of the GNU General Public License
 *along with this program; if not, write to the Free Software
 *Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 *
 * Created on 10.01.2006
 */
/*$Id: FreeMindCommon.java,v 1.1.2.2.2.39 2009/05/18 19:47:57 christianfoltin Exp $*/
package freemind.main;

import org.jetbrains.annotations.NotNull;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLClassLoader;
import java.net.URLDecoder;
import java.util.*;
import java.util.logging.Logger;

/**
 * @author foltin
 */
public class FreeMindCommon {
	public static FreeMindCommon_Extracted1 freeMindCommon_Extracted1;

	public static final String FREEMIND_FILE_EXTENSION_WITHOUT_DOT = "mm";

	public static final String FREEMIND_FILE_EXTENSION = "."
			+ FREEMIND_FILE_EXTENSION_WITHOUT_DOT;

	public static final String POSTFIX_TRANSLATE_ME = "[translate me]";

	public static class FreemindResourceBundle extends ResourceBundle {
		public PropertyResourceBundle languageResources;
		public PropertyResourceBundle defaultResources;

		public FreemindResourceBundle() {
			try {
				String lang = freeMindCommon_Extracted1.getProperty(RESOURCE_LANGUAGE);
				if (lang == null || lang.equals("automatic")) {
					lang = Locale.getDefault().getLanguage() + "_" + Locale.getDefault().getCountry();
					if (getLanguageResources(lang) == null) {
						lang = Locale.getDefault().getLanguage();
						if (getLanguageResources(lang) == null) {
							// default is english.
							lang = DEFAULT_LANGUAGE;
						}
					}
				}
				if ("no".equals(lang)) {
					// Bugs item #1935818
					lang = "nb";
				}
				languageResources = getLanguageResources(lang);
				/*
				 * fc, 26.4.2008. the following line is a bug, as the
				 * defaultResources are used, even, when a single string is
				 * missing inside a bundle and not only, when the complete
				 * bundle is missing.
				 */
				// if(languageResources == null)
				defaultResources = getLanguageResources(DEFAULT_LANGUAGE);
			} catch (Exception ex) {
				Resources.getInstance().logException(ex);
				logger.severe("Error loading Resources");
			}
			// printResourceTable();
		}

		public PropertyResourceBundle getLanguageResources(String lang)
				throws IOException {
			URL systemResource = freeMindCommon_Extracted1.getMFreeMindMain().getResource("Resources_" + lang
					+ ".properties");
			if (systemResource == null) {
				return null;
			}
			InputStream in = systemResource.openStream();
			if (in == null) {
				return null;
			}
			PropertyResourceBundle bundle = new PropertyResourceBundle(in);
			in.close();
			return bundle;
		}

		protected Object handleGetObject(@NotNull String key) {
			try {
				return languageResources.getString(key);
			} catch (Exception ex) {
				logger.severe("Warning - resource string not found:\n" + key);
				return defaultResources.getString(key) + POSTFIX_TRANSLATE_ME;
			}
		}

		public Enumeration getKeys() {
			return defaultResources.getKeys();
		}

		String getResourceString(String key) {
			try {
				return getString(key);
			} catch (Exception ex) {
				return key;
			}
		}

		String getResourceString(String key, String pDefault) {
			try {
				try {
					return languageResources.getString(key);
				} catch (Exception ex) {
					return defaultResources.getString(key)
							+ POSTFIX_TRANSLATE_ME;
				}
			} catch (Exception e) {
				// logger.info(key+" not found.");
				return pDefault;
			}
		}
	}

	public static final String RESOURCE_LANGUAGE = "language";
    public static final String CHECK_SPELLING = "check_spelling";

	public static final String RESOURCE_ANTIALIAS = "antialias";

	public static final String DEFAULT_LANGUAGE = "en";

	public static final String LOCAL_PROPERTIES = "LocalProperties.";

	public String baseDir;

	/**
	 * Holds the last opened map.
	 */
	public static final String ON_START_IF_NOT_SPECIFIED = "onStartIfNotSpecified";
	public static final String LOAD_LAST_MAP = "loadLastMap";
	public static final String LOAD_LAST_MAPS_AND_LAYOUT = "load_last_maps_and_layout";
	public static final String SAVE_ONLY_INTRISICALLY_NEEDED_IDS = "save_only_intrisically_needed_ids";

	public static final String LOAD_NEW_MAP = "load_new_map_when_no_other_is_specified";

	/**
	 * Load event occurred during startup
	 * <p>
	 * If FreeMind is not started and you double-click a .mm file on Mac OS X
	 * the .mm file is not passed to Java's main method but handleOpenFile is
	 * called which happens during startup where it is not safe to already load
	 * the map. Therefore the event is stored in this property and later
	 * processed by loadMaps.
	 * <p>
	 * Related issues
	 * <ul>
	 * <li>
	 * http://sourceforge.net/tracker/?func=detail&aid=2908045&group_id=7118&
	 * atid=107118
	 * <li>http://sourceforge.net/tracker/index.php?func=detail&aid=1980423&
	 * group_id=7118&atid=107118
	 * </ul>
	 */
	public static final String LOAD_EVENT_DURING_STARTUP = "loadEventDuringStartup";

	public static final String MINDMAP_LAST_STATE_MAP_STORAGE = "mindmap_last_state_map_storage";

	public static Logger logger = null;

	/**
	 *
	 */
	public FreeMindCommon(FreeMindMain main) {
		super();
		freeMindCommon_Extracted1 = new FreeMindCommon_Extracted1(main);

		// TODO Auto-generated constructor stub
		if (logger == null)
			logger = main.getLogger(this.getClass().getName());
	}

	public String getProperty(String key) {
		return freeMindCommon_Extracted1.getProperty(key);
	}

	/**
	 * Returns the ResourceBundle with the current language
	 */
	public ResourceBundle getResources() {
		return freeMindCommon_Extracted1.getResources();
	}

	public String getResourceString(String key) {
		return freeMindCommon_Extracted1.getResourceString(key);
	}

	public String getResourceString(String key, String pDefault) {
		return freeMindCommon_Extracted1.getResourceString(key, pDefault);
	}

	public void clearLanguageResources() {
		freeMindCommon_Extracted1.clearLanguageResources();
	}

	public ClassLoader getFreeMindClassLoader() {
		ClassLoader classLoader = this.getClass().getClassLoader();
		try {
			return new URLClassLoader(new URL[]{Tools.fileToUrl(new File(
					getFreemindBaseDir()))}, classLoader);
		} catch (MalformedURLException e) {
			Resources.getInstance().logException(e);
			return classLoader;
		}
	}

	/**
	 * Old version using String manipulation out of the classpath to find the
	 * base dir.
	 */
	public String getFreemindBaseDirOld() {
		if (baseDir == null) {
			final String classPath = System.getProperty("java.class.path");
			final String mainJarFile = "freemind.jar";
			int lastpos = classPath.indexOf(mainJarFile);
			int firstpos;
			// if freemind.jar is not found in the class path use user.dir as
			// Basedir
			if (lastpos == -1) {
				baseDir = System.getProperty("user.dir");
				logger.info("Basedir is user.dir: " + baseDir);
				return baseDir;
			}
			/*
			 * fc: Now, if freemind.jar is the first, firstpos == -1. This
			 * results in bad results in the substring method, or not??
			 */
			firstpos = classPath.lastIndexOf(File.pathSeparator, lastpos) + 1;
			lastpos -= 1;
			if (lastpos > firstpos) {
				logger.info("First " + firstpos + " and last " + lastpos
						+ " and string " + classPath);
				baseDir = classPath.substring(firstpos, lastpos);
			} else
				baseDir = "";
			final File basePath = new File(baseDir);
			baseDir = basePath.getAbsolutePath();
			logger.info("First basedir is: " + baseDir);
			/*
			 * I suppose, that here, the freemind.jar is removed together with
			 * the last path. Example: /home/foltin/freemindapp/lib/freemind.jar
			 * gives /home/foltin/freemindapp
			 */
			lastpos = baseDir.lastIndexOf(File.separator);
			if (lastpos > -1)
				baseDir = baseDir.substring(0, lastpos);
			logger.info("Basedir is: " + baseDir);
		}
		return baseDir;
	}

	/*
	 * We define the base dir of FreeMind as the directory where accessories,
	 * plugins and other things are to be found. We expect it to be either the
	 * directory where the main jar file is (freemind.jar), or the root of the
	 * class hierarchy (if no jar file is used), after any 'lib' directory is
	 * removed. One can overwrite this definition by setting the
	 * freemind.base.dir property.
	 */
	public String getFreemindBaseDir() {
		if (baseDir == null) {
			try {
				File file;
				String dir = System.getProperty("freemind.base.dir");
				if (dir == null) {
					// Property isn't set, we try to find the
					// base directory ourselves.
					// System.err.println("property not set");
					// We locate first the current class.
					String classname = this.getClass().getName();
					URL url = this.getClass().getResource(
							classname.replaceFirst("^" + this.getClass().getPackage().getName() + ".", "") + ".class");
					file = new File(URLDecoder.decode(
							url.getPath()
									.replaceFirst("^(file:|jar:)+", "")
									.replaceFirst("!.*$", "")
									.replaceFirst(
											classname.replace('.', '/')
													+ ".class$", ""), "UTF-8"));
					// if it's a file, we take its parent, a dir
					if (file.isFile())
						file = file.getParentFile();
					/*
					 * Now, we remove the lib directory: Example:
					 * /home/foltin/freemindapp/lib/freemind.jar gives
					 * /home/foltin/freemindapp
					 */
					if (file.getName().equals("lib"))
						file = file.getParentFile();
				} else {
					file = new File(dir);
				}
				// then we check if the directory exists and is really
				// a directory.
				if (!file.exists()) {
					throw new IllegalArgumentException("FreeMind base dir '"
							+ file + "' does not exist.");
				}
				if (!file.isDirectory()) {
					throw new IllegalArgumentException(
							"FreeMind base dir (!) '" + file
									+ "' is not a directory.");
				}
				// set the static variable
				baseDir = file.getCanonicalPath();
				logger.info("Basedir is: " + baseDir);
			} catch (Exception e) {
				Resources.getInstance().logException(e);
				throw new IllegalArgumentException(
						"FreeMind base dir can't be determined.");
			}
		}
		// return the value of the static variable
		return baseDir;
	}

	public String getAdjustableProperty(final String label) {
		return freeMindCommon_Extracted1.getAdjustableProperty(label);
	}

	public void loadUIProperties() {
	}

}
