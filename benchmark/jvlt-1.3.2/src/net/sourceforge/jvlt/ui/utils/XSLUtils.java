package net.sourceforge.jvlt.ui.utils;

import java.awt.Font;
import java.io.File;
import java.io.IOException;
import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.GregorianCalendar;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.multimedia.MultimediaFile;
import net.sourceforge.jvlt.multimedia.MultimediaUtils;
import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.FileUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;

import org.apache.log4j.Logger;

public class XSLUtils {
	private static final Logger logger = Logger.getLogger(XSLUtils.class);
	private static GregorianCalendar _now = new GregorianCalendar();

	public static String expired(String date_string) {
		SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
		try {
			Date date = sdf.parse(date_string);
			GregorianCalendar cal = new GregorianCalendar();
			cal.setTime(date);
			if (cal.before(_now)) {
				return "true";
			}
			return "false";
		} catch (ParseException ex) {
			return "false";
		}
	}

	public static String fontStyle(String key) {
		return fontStyleFamily(key) + "; " + fontStyleSize(key);
	}

	public static String fontStyleFamily(String key) {
		Font f = ((UIConfig) JVLT.getConfig()).getFontProperty(key);
		return f == null ? "" : "font-family: " + f.getFamily();
	}

	public static String fontStyleSize(String key) {
		Font f = ((UIConfig) JVLT.getConfig()).getFontProperty(key);
		return f == null ? "" : "font-size: " + f.getSize() + "pt";
	}

	public static String formatDate(String date_string) {
		SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
		try {
			Date date = sdf.parse(date_string);
			DateFormat format = DateFormat.getDateTimeInstance(
					DateFormat.MEDIUM, DateFormat.MEDIUM);

			return format.format(date);
		} catch (ParseException ex) {
			return date_string;
		}
	}

	public static String i18nString(String key) {
		return I18nService.getString("Labels", key);
	}

	public static String translate(String key) {
		AttributeResources resources = new AttributeResources();
		return resources.getString(key);
	}

	public static String mimeType(String file_name) {
		MultimediaFile file = MultimediaUtils
				.getMultimediaFileForName(file_name);
		switch (file.getType()) {
		case MultimediaFile.AUDIO_FILE:
			return "audio";
		case MultimediaFile.IMAGE_FILE:
			return "image";
		default:
			return "other";
		}
	}

	public static String mimeTypeImage(String file_name) {
		MultimediaFile file = MultimediaUtils
				.getMultimediaFileForName(file_name);
		if (file.getType() == MultimediaFile.AUDIO_FILE) {
			return "/images/audio.png";
		} else if (file.getType() == MultimediaFile.IMAGE_FILE) {
			return "/images/image.png";
		} else {
			// if (file.getType() == MultimediaFile.OTHER_FILE)
			return "/images/unknown.png";
		}
	}

	public static String filePath(String file_name) {
		try {
			if (FileUtils.isPathRelative(file_name)) {
				return file_name;
			}
			File f = new File(file_name);
			return f.toURI().toString();
		} catch (IOException e) {
			logger.error("Could not determine canonical path for '" + file_name
					+ "'", e);
			return null;
		}
	}
}
