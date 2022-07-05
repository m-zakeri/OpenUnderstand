package com.calculator.app.method;

public class fibonacci extends basic_operation {
    public static double calculate_to_n(double x0, double x1, int n) {
        double value = 0;
        for (int i = 0; i < n; i++) {
            // sum is only used by this method and this class,
            // so it's a good candidate for pushing it down
            value = sum(x0, x1);
            x0 = x1;
            x1 = value;
        }
        return value;
    }
}