package com.calculator.app.method;

import com.calculator.app.display.println;

// this class is semantically shouldn't be here ,
// and should be move to display package that is semantically close to this class
// so this class is a good candidate for moving class refactoring
public class printLog extends println {
    @Override
    public void print(String text) {
        super.print(text);
    }
}