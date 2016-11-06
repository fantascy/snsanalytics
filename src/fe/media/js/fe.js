function updateFollowChart(infoType)
{
	toggleInfoTypeDisplay(infoType);
	
	var chartType = document.getElementById('chartType').value
	
	if (chartType==0){
	    var chartType='follower'
	}
	else if (chartType==1){
	    var chartType='follow'
	}
	else if (chartType==2){
	    var chartType='both'
	}
	
	var id = document.getElementById('id').value
	var infoType = getInfoType()
	
	ajaxUpdate('info_detail','/fe/follow/account/chartdetail',{chartType:chartType,infoType:infoType,id:id});
}


function chooseFollowType(type)
{
    var id=document.getElementById('id').value
    var infoType = getInfoType()
    if (type.value==0){
        var chartType = 'follower'
	}
	if (type.value==1){
	    var chartType = 'follow'
	}
	if (type.value==2){
	    var chartType = 'both'
	} 
	ajaxUpdate('info_detail','/fe/follow/account/chartdetail',{id:id,chartType:chartType,infoType:infoType});
}


function submitFollowRule()
{
	$.facebox.loading();
	var form = $('form').each(function(){
		var str = $(this).serialize();
		jQuery.ajax({
			url: "/fe/follow/account/create/?type=safe",
			data: str,
			type: "POST",
			timeout:GLOBAL_TIMEOUT,
			success: function(data, textStatus){
				jQuery.facebox.close();
					if (data==''){
						//ajaxUpdate('ajax_content', ret_url);
						location.href = '#' + ret_url;
					}
					else{
						document.getElementById('ajax_content').innerHTML=data;
						pageRetrofit(jQuery('#ajax_content'));
						pageTracker._trackPageview(url);
						var scripts = document.getElementById('ajax_content').getElementsByTagName("script"); 
						for(var i=0;i<scripts.length;i++){ 
						    eval(scripts[i].innerHTML); 
						}
					}
			},
			error:function(xmlHttpRequest,error){
					jQuery.facebox.close();
					//ajaxUpdate('ajax_content', ret_url);
					location.href = '#' + ret_url;
			},
			complete:function(){
					}});
	});
}


function activateFollowRule()
{
    jQuery.getJSON("/fe/follow/account/check/", {id: String(document.getElementById('rule_id').value)}, function(json) {
        result=json.result;
        if (result == 'pass') {
            activeRule('FollowCampaign', obj_id);
            // location.href = '#/fe/follow/account/';
        } else {
            jQuery.facebox(result);
        }
    });
}


function changeListStatus(id, chid)
{
    if (document.getElementById('add_'+id).style.display=='none'){
       action = 'Exclude'
    }
    else if (document.getElementById('minus_'+id).style.display=='none'){
       action = 'Include'
    }
    jQuery.getJSON("/fe/follow/account/safelist/change", { action: action, id : id, chid: chid},
	  function(data){
	    result = data.result
	    if (result=='Included'){
	       document.getElementById('add_'+id).style.display='none'
	       document.getElementById('minus_'+id).style.display=''
	       document.getElementById('status_'+id).innerHTML=result
	    }
	    else if (result=='Excluded'){
	       document.getElementById('add_'+id).style.display=''
	       document.getElementById('minus_'+id).style.display='none'
	       document.getElementById('status_'+id).innerHTML=result
	    }
	    else if (result=='limit'){
	       jQuery.facebox(errorPage('safelist'))
	    }
	  });
}


var fe = {
    rule: {
        onScheduleTypeChange: function(element) {
            if (element.value==0){
                document.getElementById('interval_id').style.display="none";
                document.getElementById('start_id').style.display="none";
                document.getElementById('end_id').style.display="none";
            } else if(element.value==1){
                document.getElementById('interval_id').style.display="none";
                document.getElementById('start_id').style.display="";
                document.getElementById('end_id').style.display="none";
            } else if(element.value==2){
                document.getElementById('interval_id').style.display="";
                document.getElementById('start_id').style.display="";
                document.getElementById('end_id').style.display="";
            }
        },
        
        activation: function(obj_id) {
        	var obj_class_name = 'FollowCampaign';
            if (document.getElementById('img_activate_'+obj_id).style.display=="none") {
                deactiveRule(obj_class_name, obj_id);
            } else { 
                jQuery.getJSON("/fe/follow/account/check/", {id: obj_id}, function(json) {
                    result=json.result;
                    if (result == 'pass') {
                        activeRule(obj_class_name, obj_id);
                    } else {
                        jQuery.facebox(result);
                    }
                });
            }
        }
    }
}


function delete_obj_admin(id,ret_url,path){
	jQuery.get(path+"delete/admin/?id="+id+"&ret_url="+ret_url, function(data) {
	    if (data.indexOf("AjaxErrorInfo")!=-1){
            msg = data.split("&nbsp;")[1];
            msg_html = "<div class='errorlist'>" + msg + "</div>"
            jQuery.facebox(msg_html);
	    }
	    else if (data.indexOf("Exception")!=-1){
            var msg_html = "<div class='errorlist'>Failed to delete this item. Please try later.</div>"
            jQuery.facebox(msg_html);
	    }
	    else {
	       tr_object=document.getElementById('list_tr_id_'+id);
		   document.getElementById("layout_table").deleteRow(tr_object.rowIndex);      
	    }
	})
}


function errorPage(error){
	var message;
	if(error == "timeout"){
		message =  "Your request is timeout. Please retry!";
	} else if(error == "parsererror"){
		message =  "Some required data is missing!";
	} else if(error == "error"){
		message = "Could not connect to server! Please retry a few moment later.";
	} else if(error == "noChannel"){
		message = "Could not activate this campaign! All marketing channels of this campaign are deleted.";
	} else if(error == "noContent"){
		message = "Could not activate this campaign! All marketing contents of this campaign are deleted.";
	} else if(error == "safelist"){
		message = "You can have at most 3 safe lists!";
	} else if(error == "404"){
	    message = "Http Error 404: Page Not Found."
	} else {
		message = "Encountered unknown error. Please retry!"
	}
	return "<div class='errorlist'>" + message + "</div>";
}


function getTotalFollowers(id,followersMap){
	return followersMap[id];	
}


function updateTips(t) {
	$("#submit_state").empty();
	$('#submit_state').append(t);
	$('#submit_state').show();
}


function changeLikeCampaignTitle(page){
	var page_title=page.options[page.selectedIndex].text.split(' - ')[1];	
	var campaign_name=document.getElementById('like_campaign_name').value;
	document.getElementById('like_campaign_name').value=page_title;
}


function toggleFollowConfig(attr)
{
	jQuery.post('/fe/follow/account/config/toggle/', {'attr': attr}, function(data){});
}


function toggleFollowConfigCron()
{
	jQuery.post('/fe/follow/account/config/toggle/', {'attr': 'manually_stopped'}, function(data){
	    var result = data 
	    if (result=='True'){
	       document.getElementById("followMsg").innerHTML = "Stopped"
	       document.getElementById("followAction").value = "Resume Follow Cron"
	    }
	    else{
	       document.getElementById("followMsg").innerHTML = "Active"
	       document.getElementById("followAction").value = "Stop Follow Cron"
	    }
	});
}


function toggleFollowConfigStats()
{
	jQuery.post('/fe/follow/account/config/toggle/', {'attr': 'skip_stats'}, function(data){
	    var result = data 
	    if (result=='True'){
	       document.getElementById("statsMsg").innerHTML = "Inactive"
	       document.getElementById("statsAction").value = "Resume Follow Stats"
	    }
	    else{
	       document.getElementById("statsMsg").innerHTML = "Active"
	       document.getElementById("statsAction").value = "Skip Follow Stats"
	    }
	});
}


function updateFollowConfig(attr){
	var value = document.getElementById('follow-config-value').value;
	jQuery.post('/fe/follow/account/config/update/', {'attr':attr, 'value':value}, function(data){ 
	    jQuery.facebox.close();
	    location.reload() 
	})
}


function updateFollowConfigTime(attr){
	var beginHour = document.getElementById('begin-hour').value;
	var hours = document.getElementById('hours').value;
	jQuery.post('/fe/follow/account/config/update/', {'attr':attr, 'begin_hour':beginHour, 'hours':hours}, function(data){ 
	    jQuery.facebox.close();
	    location.reload() 
	})
}


function resetFollowConfig(){
	jQuery.get('/fe/follow/account/config/reset/', function(data){ 
	    location.reload() 
	})
}


function reactivateProtectedFollowCampaigns(){
	jQuery.get('/fe/follow/account/reactivate_protected/', function(data){ 
    	alert(data)
	})
}


function reactivateSuspendedFollowCampaigns(){
	jQuery.get('/fe/follow/account/reactivate_suspended/', function(data){ 
    	alert(data)
	})
}
