package com.calculator.app.init;

import com.calculator.app.method.integral;
import com.calculator.app.method.fibonacci;
import com.calculator.app.display.print_success;
import com.calculator.app.display.println;

public class Main {
    // at this point we are going to check the changes propagation when refactors are executes on this projects
    public static void main(String[] args) {
        // whe must propagate extract class when splitting integral class
        integral in = new integral();
        in.calculate_x(1, 10, 1000);
        // we must propagate print_success class termination when inline the class
        print_success.print_success_message();
        in.calculate_pow_x_n(1, 10, 1000);
        println pln = new println();
        double value = fibonacci.calculate_to_n(0, 1, 100);
        pln.print("the value of fibonacci is :", String.valueOf(value));
        // we must make sure print_success is working when inline-class terminates print_success class
        pln.print_success();
    }
}
