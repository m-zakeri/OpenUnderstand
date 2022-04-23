
class c2 extends c1 {
    int abcd;
}


class c1 {
    int abc;
}

class c3 {
    public void set(){
        c2 b = new c2();
         c1 a = (c1) b;
    }
}


