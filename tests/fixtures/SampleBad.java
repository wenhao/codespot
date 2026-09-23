public class SampleBad {
    public void run(String input) {
        try {
            int x = Integer.parseInt(input);
            System.out.println(x);
        } catch (Exception e) {
        }
        String s = new String("literal");
        if (s == "literal") { }
    }
}
