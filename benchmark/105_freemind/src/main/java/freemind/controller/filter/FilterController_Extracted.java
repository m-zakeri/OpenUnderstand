package freemind.controller.filter;

import freemind.controller.Controller;
import freemind.main.Resources;
import freemind.modes.MindIcon;
import freemind.modes.MindMap;
import freemind.modes.common.plugins.NodeNoteBase;

import javax.swing.*;

public class FilterController_Extracted {
    private Controller c;
    private FilterToolbar filterToolbar;
    private DefaultComboBoxModel filterConditionModel;

    public void setC(Controller c) {
        this.c = c;
    }

    public void setFilterToolbar(FilterToolbar filterToolbar) {
        this.filterToolbar = filterToolbar;
    }

    public DefaultComboBoxModel getFilterConditionModel() {
        return filterConditionModel;
    }

    /**
     *
     */
    public void showFilterToolbar(boolean show, MindMap thisMap) {
        if (show == isVisible())
            return;
        getFilterToolbar().setVisible(show);
        final Filter filter = thisMap.getFilter();
        if (show) {
            filter.applyFilter(c);
        } else {
            FilterController.createTransparentFilter().applyFilter(c);
        }
        refreshMap();
    }

    public void refreshMap() {
        c.getModeController().refreshMap();
    }

    public void saveConditions() {
        if (filterToolbar != null) {
            filterToolbar.saveConditions();
        }
    }

    public void setFilterConditionModel(
            DefaultComboBoxModel filterConditionModel) {
        this.filterConditionModel = filterConditionModel;
        filterToolbar.setFilterConditionModel(filterConditionModel);
    }

    /**
     *
     */
    public FilterToolbar getFilterToolbar() {
        if (filterToolbar == null) {
            filterToolbar = new FilterToolbar(c);
            filterConditionModel = (DefaultComboBoxModel) filterToolbar
                    .getFilterConditionModel();

            // FIXME state icons should be created on order to make possible
            // their use in the filter component.
            // It should not happen here.
            MindIcon.factory("AttributeExist", new ImageIcon(Resources
                    .getInstance().getResource("images/showAttributes.gif")));
            MindIcon.factory(NodeNoteBase.NODE_NOTE_ICON, new ImageIcon(
                    Resources.getInstance().getResource("images/knotes.png")));
            MindIcon.factory("encrypted");
            MindIcon.factory("decrypted");

            filterToolbar.initConditions();
        }
        return filterToolbar;
    }

    public boolean isVisible() {
        return getFilterToolbar().isVisible();
    }
}