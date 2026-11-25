// アパレルCAD のマニュアルは https://kadoya2005.github.io/apparel-cad/manual/ に移りました。
// このリポジトリのどのページを開いても、新しい場所の同じページへ移ります。
(function () {
  var rest = location.pathname.replace(/^\/apparel-cad-manual\/?/, '');
  location.replace('https://kadoya2005.github.io/apparel-cad/manual/' + rest + location.search + location.hash);
})();
