/*FreeMind - A Program for creating and viewing Mindmaps
 *Copyright (C) 2000-2001  Joerg Mueller <joergmueller@bigfoot.com>
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
/*$Id: ArrowLinkAdapter.java,v 1.4.18.5.12.1 2007/05/06 21:12:19 christianfoltin Exp $*/

package freemind.modes;

import freemind.main.FreeMindMain;
import freemind.main.Tools;
import freemind.main.XMLElement;

import java.awt.*;

public abstract class ArrowLinkAdapter extends LinkAdapter implements MindMapArrowLink {
	public ArrowLinkAdapter_Extracted1 arrowLinkAdapter_Extracted1 = new ArrowLinkAdapter_Extracted1();

	/**
	 * the zero is the start point of the line;
	 */
	protected Point startInclination;
	/**
	 * the zero is the start point of the line;
	 */
	protected Point endInclination;
	protected boolean showControlPointsFlag;

	public ArrowLinkAdapter(MindMapNode source, MindMapNode target,
							FreeMindMain frame) {
		super(source, target, frame);
		arrowLinkAdapter_Extracted1.setStartArrow2("None");
		arrowLinkAdapter_Extracted1.setEndArrow2("Default");
	}

	public Point getStartInclination() {
		if (startInclination == null)
			return null;
		return new Point(startInclination);
	}

	public Point getEndInclination() {
		if (endInclination == null)
			return null;
		return new Point(endInclination);
	}

	public String getStartArrow() {
		return arrowLinkAdapter_Extracted1.getStartArrow();
	}

	public String getEndArrow() {
		return arrowLinkAdapter_Extracted1.getEndArrow();
	}

	public void setStartInclination(Point startInclination) {
		this.startInclination = startInclination;
	}

	public void setEndInclination(Point endInclination) {
		this.endInclination = endInclination;
	}

	public void setStartArrow(String startArrow) {
		arrowLinkAdapter_Extracted1.setStartArrow(startArrow);
	}

	public void setEndArrow(String endArrow) {
		arrowLinkAdapter_Extracted1.setEndArrow(endArrow);
	}

	public Object clone() {
		ArrowLinkAdapter arrowLink = (ArrowLinkAdapter) super.clone();
		// now replace the points:
		arrowLink.startInclination = (startInclination == null) ? null
				: new Point(startInclination.x, startInclination.y);
		arrowLink.endInclination = (endInclination == null) ? null : new Point(
				endInclination.x, endInclination.y);
		arrowLink.arrowLinkAdapter_Extracted1.setStartArrow2((arrowLinkAdapter_Extracted1.getStartArrow() == null) ? null : arrowLinkAdapter_Extracted1.getStartArrow());
		arrowLink.arrowLinkAdapter_Extracted1.setEndArrow2((arrowLinkAdapter_Extracted1.getEndArrow() == null) ? null : arrowLinkAdapter_Extracted1.getEndArrow());
		return arrowLink;
	}

	public void showControlPoints(boolean bShowControlPointsFlag) {
		showControlPointsFlag = bShowControlPointsFlag;
	}

	public boolean getShowControlPointsFlag() {
		return showControlPointsFlag;
	}

	public XMLElement save() {
		XMLElement arrowLink = new XMLElement();
		arrowLink.setName("arrowlink");

		if (style != null) {
			arrowLink.setAttribute("STYLE", style);
		}
		if (getUniqueID() != null) {
			arrowLink.setAttribute("ID", getUniqueID());
		}
		if (color != null) {
			arrowLink.setAttribute("COLOR", Tools.colorToXml(color));
		}
		if (getDestinationLabel() != null) {
			arrowLink.setAttribute("DESTINATION", getDestinationLabel());
		}
		if (getReferenceText() != null) {
			arrowLink.setAttribute("REFERENCETEXT", getReferenceText());
		}
		if (getStartInclination() != null) {
			arrowLink.setAttribute("STARTINCLINATION",
					Tools.PointToXml(getStartInclination()));
		}
		if (getEndInclination() != null) {
			arrowLink.setAttribute("ENDINCLINATION",
					Tools.PointToXml(getEndInclination()));
		}
		if (getStartArrow() != null)
			arrowLink.setAttribute("STARTARROW", (getStartArrow()));
		if (getEndArrow() != null)
			arrowLink.setAttribute("ENDARROW", (getEndArrow()));
		return arrowLink;
	}

}
