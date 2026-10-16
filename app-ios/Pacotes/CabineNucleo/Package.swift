// swift-tools-version:5.10
// Lógica do modo Cabine sem UIKit nem AVFoundation: testável no Mac com `swift test`.
import PackageDescription

let package = Package(
    name: "CabineNucleo",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "CabineNucleo", targets: ["CabineNucleo"])],
    targets: [
        .target(name: "CabineNucleo"),
        .testTarget(name: "CabineNucleoTests", dependencies: ["CabineNucleo"]),
    ]
)
