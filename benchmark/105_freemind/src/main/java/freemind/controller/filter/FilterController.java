/*FreeMind - A Program for creating and viewing Mindmaps
 *Copyright (C) 2000-2006 Joerg Mueller, Daniel Polansky, Christian Foltin, Dimitri Polivaev and others.
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
 */
/*
 * Created on 05.05.2005
 * Copyright (C) 2005 Dimitri Polivaev
 */
package freemind.controller.filter;

import freemind.controller.Controller;
import freemind.controller.MapModuleManager.MapModuleChangeObserver;
import freemind.controller.filter.condition.Condition;
import freemind.controller.filter.condition.ConditionFactory;
import freemind.controller.filter.condition.ConditionRenderer;
import freemind.controller.filter.condition.NoFilteringCondition;
import freemind.main.XMLElement;
import freemind.modes.MindMap;
import freemind.modes.Mode;
import freemind.view.MapModule;

import javax.swing.*;
import java.io.*;
import java.util.Vector;

/**
 * @author dimitri
 */
public class FilterController implements MapModuleChangeObserver {
	private final FilterController_Extracted filterController_Extracted = new FilterController_Extracted();
	static private ConditionRenderer conditionRenderer = null;
	static private ConditionFactory conditionFactory;
	private MindMap map;
	static final String FREEMIND_FILTER_EXTENSION_WITHOUT_DOT = "mmfilter";
	private static Filter inactiveFilter;

	public FilterController(Controller c) {
		filterController_Extracted.setC(c);
		c.getMapModuleManager().addListener(this);
	}

	ConditionRenderer getConditionRenderer() {
		if (conditionRenderer == null)
			conditionRenderer = new ConditionRenderer();
		return conditionRenderer;
	}

	/**
	 *
	 */
	public FilterToolbar getFilterToolbar() {
		return filterController_Extracted.getFilterToolbar();
	}

	/**
	 *
	 */
	public void showFilterToolbar(boolean show) {
		filterController_Extracted.showFilterToolbar(show, this.map);
	}

	public boolean isVisible() {
		return filterController_Extracted.isVisible();
	}

	void refreshMap() {
		filterController_Extracted.refreshMap();
	}

	static public ConditionFactory getConditionFactory() {
		if (conditionFactory == null)
			conditionFactory = new ConditionFactory();
		return conditionFactory;
	}

	/**
	 *
	 */
	public MindMap getMap() {
		return map;
	}

	public boolean isMapModuleChangeAllowed(MapModule oldMapModule,
											Mode oldMode, MapModule newMapModule, Mode newMode) {
		return true;
	}

	public void beforeMapModuleChange(MapModule oldMapModule, Mode oldMode,
									  MapModule newMapModule, Mode newMode) {
	}

	public void afterMapClose(MapModule pOldMapModule, Mode pOldMode) {
	}

	public void afterMapModuleChange(MapModule oldMapModule, Mode oldMode,
									 MapModule newMapModule, Mode newMode) {
		MindMap newMap = newMapModule != null ? newMapModule.getModel() : null;
		FilterComposerDialog fd = filterController_Extracted.getFilterToolbar().getFilterDialog();
		if (fd != null) {
			fd.mapChanged(newMap);
		}
		map = newMap;
		filterController_Extracted.getFilterToolbar().mapChanged(newMap);
	}

	public void numberOfOpenMapInformation(int number, int pIndex) {
	}

	public static Filter createTransparentFilter() {
		if (inactiveFilter == null)
			inactiveFilter = new DefaultFilter(
					NoFilteringCondition.createCondition(), true, false);
		return inactiveFilter;

	}

	public void saveConditions() {
		filterController_Extracted.saveConditions();
	}

	public DefaultComboBoxModel getFilterConditionModel() {
		return filterController_Extracted.getFilterConditionModel();
	}

	public void setFilterConditionModel(
			DefaultComboBoxModel filterConditionModel) {
		filterController_Extracted.setFilterConditionModel(filterConditionModel);
	}

	void saveConditions(DefaultComboBoxModel filterConditionModel,
						String pathToFilterFile) throws IOException {
		XMLElement saver = new XMLElement();
		saver.setName("filter_conditions");
		Writer writer = new FileWriter(pathToFilterFile);
		for (int i = 0; i < filterConditionModel.getSize(); i++) {
			Condition cond = (Condition) filterConditionModel.getElementAt(i);
			cond.save(saver);
		}
		saver.write(writer);
		writer.close();
	}

	void loadConditions(DefaultComboBoxModel filterConditionModel,
						String pathToFilterFile) throws IOException {
		filterConditionModel.removeAllElements();
		XMLElement loader = new XMLElement();
		Reader reader = new FileReader(pathToFilterFile);
		loader.parseFromReader(reader);
		reader.close();
		final Vector conditions = loader.getChildren();
		for (Object condition : conditions) {
			filterConditionModel.addElement(FilterController
					.getConditionFactory().loadCondition(
							(XMLElement) condition));
		}
	}
}
