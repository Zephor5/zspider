;+function($, window){
    var D = window.document,
        spider = {
            getReadableStr: function(r){
                var i,sx='api,';
                r = r.split(/_| |-/);
                for(i = 0; i < r.length; i++){
                    if(sx.indexOf(r[i]) > -1){
                        r[i] = r[i].toUpperCase();
                    }
                    else{
                        r[i] = r[i][0].toUpperCase() + r[i].slice(1);
                    }
                }
                return r.join(' ');
            },
            fuzzyEq: function(a, b){
                var _temp = b.split('/');
                if(_temp.indexOf('edit') == _temp.length-2 &&
                    a.indexOf(_temp[_temp.length-3] + '/list') > 0){
                    return true;
                }
                if(a.length > b.length){
                    _temp = a;
                    a = b;
                    b = _temp;
                }
                return b.slice(0, a.length) === a;
            },
            getExt: function(r){
                var _temp = r.split('.');
                return _temp[_temp.length-1];
            },
            isEmptyObj: function(o){
                var _prop, _o = new Object();
                if(typeof o === 'object'){
                    for (_prop in o) {
                        if(!_o.hasOwnProperty(_prop)){
                            return false;
                        }
                    }
                    return true;
                }

                return false;
            }
        };
    if(!window.zspider) window.zspider = spider;
}(jQuery, window);