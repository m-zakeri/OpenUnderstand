/*FreeMind - A Program for creating and viewing Mindmaps
 *Copyright (C) 2000-2004  Joerg Mueller, Daniel Polansky, Christian Foltin and others.
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
 * Created on 25.08.2004
 */
/*$Id: MacChanges.java.not_here,v 1.1.4.6.2.9 2009/05/19 18:28:12 christianfoltin Exp $*/
package accessories.plugins;

import java.io.File;
import java.util.logging.Logger;

import javax.swing.SwingUtilities;

import com.apple.eawt.Application;
import com.apple.eawt.ApplicationAdapter;
import com.apple.eawt.ApplicationEvent;

import freemind.controller.Controller;
import freemind.controller.Controller.LocalLinkConverter;
import freemind.main.FreeMindCommon;
import freemind.main.FreeMindMain;
import freemind.main.Tools;

/** This plugin changes some things for mac users.
 * @author foltin
 */
public class MacChanges extends ApplicationAdapter  {

	private static final String FREE_MIND_JAVA = "FreeMind.app/Contents/Resources/Java";

	private Logger logger;
	
	private static Application fmMacApplication;

	private final FreeMindMain mFrame;

	private boolean mIsStartupPhase = false;
	
	private int loadEventsDuringStartup = 0;
	
	public MacChanges(FreeMindMain pFrame) {
		mFrame = pFrame;
		logger = pFrame.getLogger(this.getClass().getName());
		logger.info("Performing Mac Changes.");
		pFrame.setProperty("keystroke_add_child", pFrame.getProperty("keystroke_add_child_mac"));
		pFrame.setProperty("load_new_map_when_no_other_is_specified", "false");
		Controller.localDocumentationLinkConverter = new LocalLinkConverter(){

			public String convertLocalLink(String link) {
				return "file:" + System.getProperty("user.dir")
				//TODO: retrieve name of application and don't use the fixed FreeMind.app here.
						+ "/" +
								FREE_MIND_JAVA + "/" + link;
			}}; 
		if(fmMacApplication==null){
			// if a handleOpen comes here, directly, we know that FM is currently starting.
			mIsStartupPhase = true;
			logger.info("Adding application listener.");
			fmMacApplication = Application.getApplication();
			fmMacApplication.addApplicationListener(this);
			fmMacApplication.addPreferencesMenuItem();
			fmMacApplication.addAboutMenuItem();
			fmMacApplication.setEnabledPreferencesMenu(true);
//			fmMacApplication.removePreferencesMenuItem();
			mIsStartupPhase = false;
		}
		logger.info("Performed Mac Changes.");
	}


	public void handleQuit(ApplicationEvent event) {
		SwingUtilities.invokeLater(new Runnable() {
			public void run() {
				mFrame.getController().quit.actionPerformed(null);
			}
		});
		event.setHandled(true);
		// this is intentionally done:
		throw new IllegalStateException("Stop Pending User Confirmation");
	}

	public void handleAbout(ApplicationEvent event) {
		mFrame.getController().about.actionPerformed(null);
		event.setHandled(true);
	}
	public void handleOpenFile(final ApplicationEvent event) {
		try {
			if(mIsStartupPhase) {
				logger.info("Later loading " + event.getFilename());
				mFrame.setProperty(FreeMindCommon.LOAD_EVENT_DURING_STARTUP + loadEventsDuringStartup, event.getFilename());
				++loadEventsDuringStartup;
			} else {
				logger.info("Direct loading " + event.getFilename());
				mFrame.getController().getModeController().load(
							Tools.fileToUrl(new File(event.getFilename())));
			}
			event.setHandled(true);
		} catch (Exception e) {
			freemind.main.Resources.getInstance().logException(e);
		}
	}
	
	public void handlePreferences(ApplicationEvent event) {
		mFrame.getController().propertyAction.actionPerformed(null);
		event.setHandled(true);
	}
}