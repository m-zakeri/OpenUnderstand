class c1 {
	int a;
}
class c2 extends c1 {
	int b;
}
class c3 {
 c2 b = new c2();
 c1 a = (c1) b;
}