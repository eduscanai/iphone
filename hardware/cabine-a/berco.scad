// Berço da cabine A — paramétrico (guia 10.1).
// Exportar:  openscad -D 'peca="berco"' -o berco.stl berco.scad
//            openscad -D 'peca="suporte_espelho"' -o suporte_espelho.stl berco.scad
//            openscad -D 'peca="suporte_led"' -o suporte_led.stl berco.scad
// Unidades: mm. Imprimir em PLA/PETG preto fosco.

/* [Peça] */
peca = "berco"; // [berco, suporte_espelho, suporte_led, montagem]

/* [Placa] */
placa_largura   = 260;  // eixo X (lado curto do aparelho fica em X)
placa_profund   = 250;  // eixo Y: aparelho (≤ 163) + espelhos de topo e base
placa_espessura = 5;

/* [Aparelho] — o maior modelo atendido define as folgas */
aparelho_larg_max = 78.1;   // iPhone 12/13/14 Plus/Pro Max
aparelho_alt_max  = 163.0;  // iPhone 16 Pro Max
origem_x = 70;              // quina topo/lado do volume encosta aqui
origem_y = 42;              // deixa espaço para o espelho do topo

/* [Batente] — só nas quinas: um L contínuo esconderia a base das laterais nos espelhos */
batente_altura   = 3;     // ≤ 3 mm: não faz sombra na luz rasante (guia 10.1)
batente_espessura = 3;
batente_braco    = 12;    // comprimento de cada braço do L na quina

/* [Marcadores ArUco] — 30 mm de preto + 5 mm de margem branca (folha impressa) */
aruco_lado   = 30;
aruco_margem = 5;
aruco_rebaixo = 0.4;      // espessura do papel/adesivo

/* [Feltro nas áreas de apoio] */
feltro_rebaixo = 1.0;
feltro_largura = 10;

/* [Espelhos 45° (D3 = espelhos)] */
espelho_largura = 12;     // faixa refletora: 12 × sin 45° ≈ 8,5 mm cobre a espessura (≤ 8,3 mm).
                          // NÃO aumentar sem testar: a cunha fica entre a barra rasante e o
                          // aparelho; mais alta que ~8–9 mm, faz sombra na tela (ver README).
espelho_compr   = 170;    // laterais; topo/base usam espelho_compr_curto
espelho_compr_curto = 90;
espelho_espessura = 3;    // espelho de primeira superfície (evita imagem dupla)
trilho_largura  = 8;
trilho_profund  = 2.5;
trilho_curso    = 20;     // ajuste da distância espelho–aparelho

/* [Barras de LED] */
led_altura_eixo = 15;     // centro da barra a 1–2 cm da mesa (guia 10.1)
led_perfil_larg = 17;     // perfil de alumínio com difusor (medir o comprado)
led_perfil_alt  = 8;

$fn = 48;
folga = 0.3;

// ------------------------------------------------------------------ placa

module bolsao_aruco(x, y) {
    l = aruco_lado + 2 * aruco_margem + 2 * folga;
    translate([x, y, placa_espessura - aruco_rebaixo]) cube([l, l, aruco_rebaixo + 0.01]);
}

module batente_quina(x, y, sx, sy) {
    // L com braços apontando para +sx e +sy a partir da quina (x, y)
    translate([x, y, placa_espessura]) {
        translate([sx > 0 ? -batente_espessura : 0, sy > 0 ? -batente_espessura : -batente_braco, 0])
            cube([batente_espessura, batente_braco + batente_espessura, batente_altura]);
        translate([sx > 0 ? -batente_espessura : -batente_braco, sy > 0 ? -batente_espessura : 0, 0])
            cube([batente_braco + batente_espessura, batente_espessura, batente_altura]);
    }
}

module trilho(x, y, comp, ao_longo_x) {
    translate([x, y, placa_espessura - trilho_profund])
        if (ao_longo_x) cube([comp, trilho_largura + trilho_curso, trilho_profund + 0.01]);
        else cube([trilho_largura + trilho_curso, comp, trilho_profund + 0.01]);
}

module berco() {
    difference() {
        cube([placa_largura, placa_profund, placa_espessura]);
        // feltro: duas faixas sob o aparelho (apoio sem riscar)
        for (fy = [origem_y + 25, origem_y + aparelho_alt_max - 25 - feltro_largura])
            translate([origem_x + 8, fy, placa_espessura - feltro_rebaixo])
                cube([aparelho_larg_max - 16, feltro_largura, feltro_rebaixo + 0.01]);
        // marcadores nos 4 cantos da placa, fora da área do aparelho e dos espelhos
        a = aruco_lado + 2 * aruco_margem;
        bolsao_aruco(4, 4);
        bolsao_aruco(placa_largura - a - 4 - 2 * folga, 4);
        bolsao_aruco(4, placa_profund - a - 4 - 2 * folga);
        bolsao_aruco(placa_largura - a - 4 - 2 * folga, placa_profund - a - 4 - 2 * folga);
        // trilhos dos espelhos: lat_esq (x−), lat_dir (x+), topo (y−) e base (y+)
        dx = 6 + trilho_largura + trilho_curso;   // da borda do aparelho até o fim do trilho
        trilho(origem_x - dx, origem_y + 5, espelho_compr - 20, false);
        trilho(origem_x + aparelho_larg_max + 6, origem_y + 5, espelho_compr - 20, false);
        trilho(origem_x + 5, origem_y - dx, espelho_compr_curto - 10, true);
        trilho(origem_x + 5, origem_y + aparelho_alt_max + 6, espelho_compr_curto - 10, true);
    }
    // batentes nas duas quinas do lado de origem (topo/lado do volume)
    batente_quina(origem_x, origem_y, 1, 1);
    batente_quina(origem_x + aparelho_larg_max + 2, origem_y, -1, 1);
}

// ------------------------------------------------------------------ peças avulsas

module suporte_espelho(comp = espelho_compr) {
    // cunha a 45° com rebaixo para o espelho e uma aleta que corre no trilho
    h = espelho_largura * sin(45) + 1;  // altura da cunha = topo do espelho + 1 mm
    difference() {
        union() {
            rotate([90, 0, 90]) linear_extrude(comp) polygon([[0, 0], [h, 0], [0, h]]);
            translate([0, 0, -trilho_profund + folga]) cube([comp, trilho_largura - 2 * folga, trilho_profund - folga]);
        }
        // assento do espelho na face inclinada
        translate([-0.01, 0, 0]) rotate([45, 0, 0]) translate([0, 1.5, -espelho_espessura + 0.01])
            cube([comp + 0.02, espelho_largura + 2 * folga, espelho_espessura + 0.01]);
    }
}

module suporte_led() {
    // garra para o perfil da barra de LED, eixo a led_altura_eixo da mesa
    base = 30;
    difference() {
        union() {
            cube([base, 20, 3]);
            translate([0, 0, 0]) cube([4, 20, led_altura_eixo + led_perfil_alt / 2 + 3]);
        }
        translate([-0.01, (20 - led_perfil_larg) / 2, led_altura_eixo - led_perfil_alt / 2])
            cube([4.02, led_perfil_larg + 2 * folga, led_perfil_alt + 2 * folga]);
        translate([base - 8, 10, -0.01]) cylinder(d = 4.2, h = 3.02); // parafuso na mesa
    }
}

// ------------------------------------------------------------------ seleção

if (peca == "berco") berco();
else if (peca == "suporte_espelho") suporte_espelho();
else if (peca == "suporte_led") suporte_led();
else if (peca == "montagem") {
    // prévia: iPhone 13 encostado nas quinas, espelhos a 6 mm das bordas
    ap = [71.5, 146.7, 7.65];
    h = espelho_largura * sin(45) + 1;  // largura da cunha no chão
    berco();
    color("gray", 0.5) translate([origem_x, origem_y, placa_espessura]) cube(ap);
    color("silver") {
        // a face inclinada aponta para o aparelho
        translate([origem_x - 6 - h, origem_y + 5 + espelho_compr - 20, placa_espessura])
            rotate([0, 0, -90]) suporte_espelho(espelho_compr - 20);
        translate([origem_x + ap[0] + 6 + h, origem_y + 5, placa_espessura])
            rotate([0, 0, 90]) suporte_espelho(espelho_compr - 20);
        translate([origem_x + 5, origem_y - 6 - h, placa_espessura]) suporte_espelho(espelho_compr_curto - 10);
        translate([origem_x + 5 + espelho_compr_curto - 10, origem_y + ap[1] + 6 + h, placa_espessura])
            rotate([0, 0, 180]) suporte_espelho(espelho_compr_curto - 10);
    }
}
