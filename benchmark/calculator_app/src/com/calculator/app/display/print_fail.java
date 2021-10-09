package com.calculator.app.display;

import java.lang.System;

// this class is a candidate for inline-class refactoring
// because they have not too much responsibility and there is not any plan to add new responsibility

public class print_fail {
    public void print_fail_message() {
        System.out.println("operation encountered an error");
    }
}