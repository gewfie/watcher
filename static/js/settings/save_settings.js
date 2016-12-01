$(document).ready(function () {

/* grab all settings and write them to the config writer */
    $("button#save_settings").click(function(e){
        $this = $(this);
        $this_span = $this.children(':first');
        $this.css('background-color', '#212121');
        $this.css('color', 'white');
        $this.width('2.5em');
        $this_span.text('').addClass('fa-circle-o-notch fa-spin');

        //check if only one downloader is active:
        var enabled = 0
        $('ul#downloader > li > i.toggle').each(function(){
            if($(this).attr('value') == 'true'){
                enabled++;
            }
        });

        if(enabled > 1){
            swal("", "Please enable only one downloader.", "warning");
            return
        }

        var post_list = {};

        // SEARCH options
        var Search = {};
        $("ul#search i.toggle").each(function(){
            Search[$(this).attr("id")] = $(this).attr("value");
        })
        $("ul#search :input").each(function(){
            Search[$(this).attr("id")] = $(this).val();
        });
        post_list["Search"] = Search;

        // INDEXER options
        // The order of these tend to get jumbled. I think it sorts alphabetically, but I haven't put much effort into it yet because it really doesn't affect usage.
        var Indexers = {};
        var ind = 1;

        $("#newznab_list li").each(function(){
            if ($(this).attr("class") == "newznab_indexer"){
                var check = $(this).children("i.newznab_check").attr('value');
                var url = $(this).children("input.newznab_url").val();
                var api = $(this).children("input.newznab_api").val();

                // check if one field is blank and both are not blank
                if ( (url == "" || api == "") && (url + api !=="") ){
                    swal("", "Please complete or clear out incomplete providers.", "warning");
                    Indexers = {}
                    return
                }
                // but ignore it if both are blank
                else if (url + api !=="") {
                    var data = [url, api, check].toString().toLowerCase();
                    Indexers[ind] = data;
                    ind++;
                }
            }
        });
        post_list["Indexers"] = Indexers;

        // QUALITY options. This has a lot of data, so this wil get messy.
        var Quality = {},
            tmp = {};

        var q_list = []
        $("ul#resolution i.toggle").each(function(){
            q_list.push( $(this).attr("id") );
        });

        // enabled resolutions
        $("ul#resolution i.toggle").each(function(){
            tmp[$(this).attr("id")] = $(this).attr("value");
        });
        // order of resolutions
        var arr = $("ul#resolution").sortable("toArray");
        arr.shift();
        $.each(arr, function(i, v){
            tmp[v] = i;
        });
        // min/max sizes
        $("#resolution_size :input").each(function(){
            tmp[$(this).attr("id")] = $(this).val();
        });

        $.each(q_list, function(i, v){
            var enabled = v,
                priority = v + "priority",
                min = v + "min",
                max = v + "max";
            var dt = [tmp[enabled], tmp[priority], tmp[min], tmp[max]]
            Quality[v] = dt.join();
        });

        post_list["Quality"] = Quality;

        // FILTERS options.
        var Filters = {};
        $("ul#filters li input").each(function(){
            var val = $(this).val().split(", ").join(",");
            Filters[$(this).attr("id")] = val;
        });
        post_list["Filters"] = Filters;

        // DOWNLOADER options.
        var Sabnzbd = {};
        Sabnzbd["sabenabled"] = $("i#sabenabled").attr("value");
        $("ul#sabnzbd li input").each(function(){
            Sabnzbd[$(this).attr("id")] = $(this).val()
        });
        $("ul#sabnzbd li select").each(function(){
            Sabnzbd[$(this).attr("id")] = $(this).val()
        });
        post_list["Sabnzbd"] = Sabnzbd;

        var NzbGet = {};
        NzbGet["nzbgenabled"] = $("i#nzbgenabled").attr("value");
        $("ul#nzbget li i.toggle").each(function(){
            NzbGet[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#nzbget li input").not("[type=button]").each(function(){
            NzbGet[$(this).attr("id")] = $(this).val();
        });
        $("ul#nzbget li select").each(function(){
            NzbGet[$(this).attr("id")] = $(this).val()
        });
        post_list["NzbGet"] = NzbGet;


        // POSTPROCESSING options
        var Postprocessing = {}
        $("ul#postprocessing li i.toggle").each(function(){
            Postprocessing[$(this).attr("id")] = $(this).attr("value");
        });
        $("ul#postprocessing li input").not("[type=button]").each(function(){
            Postprocessing[$(this).attr("id")] = $(this).val();
        });

        post_list["Postprocessing"] = Postprocessing;

        // SERVER options
        var Server = {}
        $("#server i.toggle").each(function(){
            Server[$(this).attr("id")] = $(this).attr("value");
        });
        $("#server :input").each(function(){
            Server[$(this).attr("id")] = $(this).val();
        });

        post_list["Server"] = Server;

        // make it pretty.
        var post_data = JSON.stringify(post_list)

        // Whew, finally got all of the data. That wasn"t so bad.

        $.post("/save_settings", {
            "data": post_data
        })

        .done(function(r) {
            if(r == 'failed'){
                swal("Error", "Unable to save settings. Check log for more information.", "error")
            }
            else if(r == 'success'){
                swal("Settings Saved", "", "success")
            }

            $this.removeAttr('style');
            $this_span.text('Save Settings').removeClass('fa fa-circle-o-notch fa-spin');
        });

        e.preventDefault();
    });
});
