package com.calculator.app.display;

import com.calculator.app.display.print_success;
import com.calculator.app.display.print_fail;

import java.lang.System;

public class println {

    public void print(String text) {
        System.out.println(text);
    }

    public void print(String tag, String text) {
        System.out.println(tag + " : " + text);
    }

    // inline-class refactoring should successfully inline 2 print_success and print_fail classes

    public void print_success() {
        // we intentionally made print_success_message static
        print_success.print_success_message();
    }

    public void print_fail() {
        // we intentionally made print_fail_message non-static
        print_fail pf = new print_fail();
        pf.print_fail_message();
    }
}