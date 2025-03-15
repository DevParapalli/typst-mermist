#import "@preview/jogs:0.2.3": compile-js, call-js-function, eval-js, list-global-property

#set page(height: auto, width: auto, fill: black, margin: 1em)
#set text(fill: white)

#let mermaid-src = read("./mermaid.js")
#let mermaid-bytecode = compile-js(mermaid-src)

// #list-global-property(mermaid-bytecode)

// #call-js-function(mermaid-bytecode, "initialize")

// // #let render(src, ..args) = {
  
// // }

// #let test_svg = call-js-function(mermaid-bytecode, "render", "test", "graph TB\na-->b")

// #test_svg