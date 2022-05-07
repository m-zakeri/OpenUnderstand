package com.calculator.app.display;

import java.lang.System;

// this class is a candidate for inline-class refactoring
// because they have not too much responsibility and there is not any plan to add new responsibility
public class print_success {

    public static void print_success_message() {
        System.out.println("operation has been done successfully");
    }
}