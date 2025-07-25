gate custom1 a { h a; x a; rx(0.5) a; } gate custom2(p) b { custom1 b; ry(p) b;
} gate custom3(p, q) c, d { custom2(p) c; rz(q) c; cx c, d; }
