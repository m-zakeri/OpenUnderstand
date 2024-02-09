public class PasswordValidatorMain {
public static void main(String[] args) {
String input = "Your password input here";
PasswordValidatorLexer lexer = new PasswordValidatorLexer(CharStreams.fromString(input));
CommonTokenStream tokens = new CommonTokenStream(lexer);
PasswordValidatorParser parser = new PasswordValidatorParser(tokens);
ParseTree tree = parser.password();
boolean isValid = tree.getText().equals(input);
System.out.println(isValid);
}
}
private class PasswordValidatorLexer{
}
private class CommonTokenStream {
}

private class PasswordValidatorParser {
}
