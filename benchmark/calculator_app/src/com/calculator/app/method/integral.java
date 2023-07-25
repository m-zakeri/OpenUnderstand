package com.calculator.app.method;

import com.calculator.app.method.printLog;

// the integral class is a candidate for extract class refactoring
public class integral extends basic_operation {
    private double _value_1 = 0;
    private double _value_2 = 0;
    private double _value_3 = 0;

    public double calculate_x(double from, double to, int n) {
        this._value_1 = 0;
        double range = to - from;
        double len = (range / n);
        for (int i = 0; i < n; i++) {
            // method multiplication is being used by two methods of this class
            this._value_1 += multiplication(len, i);
        }
        new printLog().print("calculated integral is: " + this._value_1);
        return this._value_1;
    }

    public double calculate_pow_x_n(double from, double to, int n) {
        this._value_2 = 0;
        double range = to - from;
        double len = (range / n);
        for (int i = 0; i < n; i++) {
            // pow only is used by this method and this class . pow is a candidate for pushing it down
            // method multiplication is being used by two methods of this class
            this._value_2 += multiplication(len, pow(i, 2));
        }
        new printLog().print("calculated integral is: " + this._value_2);
        return this._value_2;
    }
    public double calculate_rectangle(int width, int height)
    {
        this._value_3 = width*height;
        return this._value_3;
    }
}