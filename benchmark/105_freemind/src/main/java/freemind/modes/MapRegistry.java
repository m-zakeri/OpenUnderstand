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
 * Created on 26.05.2005
 *
 */
package freemind.modes;

import freemind.controller.filter.util.SortedMapListModel;
import freemind.modes.attributes.AttributeRegistry;
import freemind.modes.attributes.NodeAttributeTableModel;

import java.io.IOException;
import java.io.Writer;

/**
 * @author dimitri 26.05.2005
 */
public class MapRegistry {
	private final MapRegistry_Extracted1 mapRegistry_Extracted1 = new MapRegistry_Extracted1();
	private final AttributeRegistry attributes;
	private final MindMap map;
	private final ModeController modeController;

	public MapRegistry(MindMap map, ModeController modeController) {
		super();
		this.map = map;
		this.modeController = modeController;
		mapRegistry_Extracted1.setMapIcons(new SortedMapListModel());
		attributes = new AttributeRegistry(this);
	}

	public void addIcon(MindIcon icon) {
		mapRegistry_Extracted1.addIcon(icon);
	}

	/**
	 *
	 */
	public SortedMapListModel getIcons() {
		return mapRegistry_Extracted1.getMapIcons();
	}

	public AttributeRegistry getAttributes() {
		return attributes;
	}

	public void registrySubtree(MindMapNode root, boolean registerMyself) {
		mapRegistry_Extracted1.registrySubtree(root, registerMyself, this);
	}

	public void registryAttributes(MindMapNode node) {
		NodeAttributeTableModel model = node.getAttributes();
		if (model == null) {
			return;
		}
		for (int i = 0; i < model.getRowCount(); i++) {
			attributes.registry(model.getAttribute(i));
		}
	}

	public MindMap getMap() {
		return map;
	}

	public ModeController getModeController() {
		return modeController;
	}

	/**
	 */
	public void save(Writer fileout) throws IOException {
		getAttributes().save(fileout);
	}
}
