package freemind.main;

import freemind.main.FreeMindCommon.FreemindResourceBundle;

import java.io.IOException;
import java.util.ResourceBundle;

public class FreeMindCommon_Extracted1 {
    private final FreeMindMain mFreeMindMain;
    private FreemindResourceBundle resources;

    public FreeMindCommon_Extracted1(FreeMindMain main) {
        this.mFreeMindMain = main;
    }

    public FreeMindMain getMFreeMindMain() {
        return mFreeMindMain;
    }

    public String getProperty(String key) {
        return mFreeMindMain.getProperty(key);
    }

    public void setDefaultProperty(String key, String value) {
        mFreeMindMain.setDefaultProperty(key, value);
    }

    public String getResourceString(String key, String pDefault){
        return ((FreeMindCommon.FreemindResourceBundle) getResources()).getResourceString(key,
                pDefault);
    }

    public String getAdjustableProperty(final String label) {
        String value = getProperty(label);
        if (value == null) {
            return value;
        }
        if (value.startsWith("?") && !value.equals("?")) {
            // try to look in the language specific properties
            String localValue = ((FreeMindCommon.FreemindResourceBundle) getResources())
                    .getResourceString(FreeMindCommon.LOCAL_PROPERTIES + label, null);
            value = localValue == null ? value.substring(1).trim() : localValue;
            setDefaultProperty(label, value);
        }
        return value;
    }

    /**
     * Returns the ResourceBundle with the current language
     */
    public ResourceBundle getResources(){
        if (resources == null) {
            resources = new FreeMindCommon.FreemindResourceBundle();
        }
        return resources;
    }

    public void clearLanguageResources() {
        resources = null;
    }

    public String getResourceString(String key){
        return ((FreeMindCommon.FreemindResourceBundle) getResources()).getResourceString(key);
    }
}