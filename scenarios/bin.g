world {}

top (world){
    shape:ssBox, Q:<t(0 0 .5) d(0 0 0 1)>, size:[.5 .5 .1 .02], color:[1 1 .5]
    contact, logical:{ }
    friction:1
}

bk_wall (top){
    shape:ssBox, Q:<t(.25 0 -.25) d(90 0 90 1)>, size:[.5 .5 .1 .02], color:[1 1 .5]
    contact, logical:{ }
    friction:1
}

rg_wall (top){
    shape:ssBox, Q:<t(0 .25 -.25) d(90 90 0 1)>, size:[.5 .5 .1 .02], color:[1 1 .5]
    contact, logical:{ }
    friction:1
}

lf_wall (top){
    shape:ssBox, Q:<t(0 -.25 -.25) d(90 90 0 1)>, size:[.5 .5 .1 .02], color:[1 1 .5]
    contact, logical:{ }
    friction:1
}
