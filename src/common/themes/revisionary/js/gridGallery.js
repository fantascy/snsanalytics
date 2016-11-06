/**
 * Copyright (c) 2010 Andy Wilkerson (Parallelus)
 *
 * Version: 1.0
 * Requires: jQuery v1.4.2 or later
 *
 */

jQuery(document).ready(function($) {

	// set up the description text container
	if ( $('#GridGalleryDescription').length <= 0) {
		$('.left_content:eq(1)').append('<div id="GridGalleryDescription"></div>');
	}
	
	var currentGridIndex = '';
	
	// setup click event for gallery items (thumbnails)
	$('a.gridThumb').click( function() {
		
		currentGridIndex = jQuery(this).parent('li'); // set the index # for the current item
		
		// if the preview image is hidden, show it
		if (jQuery('#GridItemPreview').css('display') != 'block') {
			// hide thumbnails
			jQuery('#GalleryGrid ul').animate({opacity: 0},500,'easeInOutCubic',function() {
				// Animation complete.
				jQuery(this).css('visibility','hidden');
			});
			
			// add shadow to image
			jQuery('#GridItemImage').css({
				'-moz-box-shadow': '0 0 10px #333',
				'-webkit-box-shadow': '0 0 10px #333',
				'box-shadow': '0 0 10px #333'
			});
			
			// show preview image
			jQuery('#GridItemPreview').css({display:'block',opacity:0}).animate({opacity:1},700,'easeInOutCubic',function() {
				// Animation complete.
			});
		}
		
		// show loading graphic
		jQuery('#GridImageWrap').addClass('isLoading');
		
		// get the large image and insert into preview
		var img = new Image();
		
		// load the new image
		jQuery(img)
			// once the image has loaded, execute this code
			.load(function () {
				
				jQuery(this).css('opacity',0);	// set the image hidden by default    
				jQuery('#GridImageWrap').removeClass('isLoading'); // remove loading graphic
				
				// place the image in a hidden container
				tempImg = jQuery('<div id="Temp_Image"></div>').html(this)
					.css({
						'width': '1px',
						'height': '1px',
						'overflow': 'hidden',
						'visibility': 'hidden',
						'position': 'absolute',
						'bottom': '0px',
						'right': '0px'
					}).appendTo('body');
				toWidth = jQuery(this).width();		// get new image width
				toHeight = jQuery(this).height();	// get new image height
				
				// destroy the temp container
				tempImg.remove();
				
				// insert the image
				jQuery('#GridItemImage').html(this)
					.animate({ 
						width: toWidth + 'px',	// stretch width of container
						height: toHeight + 'px'	// stretch height of container
					}, 250)	
					.children(this).animate({opacity: 1}, 1000, function() {	// show new image
					
						// adjust main container (page) height if needed
						if ( (jQuery(this).height() + 90) > jQuery('#GalleryGrid').height() ) {
							// if the gallery container is too small enlarge it
							jQuery('#GalleryGrid').animate({height: jQuery(this).height() + 90 + 'px' }, 'fast');
						}
					});
				
			})
			.error(function () {
				// do this if there is an error...
			})		
			.attr('src', jQuery(this).attr('href')); // the src attribute of the new image "/myImages/myImg.jpg"
		
		// update the item description text
		var desc = jQuery(this).next('.gridItemInfo').html();
		
		// IE sucks, so we'll skip the text fading
		if (jQuery.browser.msie && parseInt(jQuery.browser.version, 10) <= 7) {
			// all other browsers fade the description text
			jQuery('#GridGalleryDescription').hide().html(desc);
			jQuery('#GridGalleryDescription').show();
		} else {
			// all other browsers fade the description text
			jQuery('#GridGalleryDescription').css('opacity',0).html(desc);
			jQuery('#GridGalleryDescription').animate({opacity: 1},1000,'easeOutCubic');
		}
		// refresh any heading tags using font replace
		Cufon.refresh() 
		
		return false;
	});

	// close button
	$('#GridPreviewClose').click( function() {
		
		// hide the preview
		jQuery('#GridItemPreview').animate({opacity:0},'easeOutCubic',function() {
			// Animation complete.
			jQuery(this).css('display','none'); // hide it so the thumbnails are clickable again
		});
		
		// show the thumbnails
		jQuery('#GalleryGrid ul').css('visibility','visible').animate({opacity: 1},750,'easeOutCubic');
		
		// clear the item description
		// IE sucks, so we'll skip the text fading
		if (jQuery.browser.msie && parseInt(jQuery.browser.version, 10) <= 7) {
			// all other browsers fade the description text
			jQuery('#GridGalleryDescription').hide();
		} else {
			// all other browsers fade the description text
			jQuery('#GridGalleryDescription').animate({opacity:0},500,'easeInCubic');
		}

		return false;
	})
	
	// next button
	$('#GridNext').click( function() {
		
		currentGridIndex.next('li').children('a.gridThumb').trigger('click');

		return false;
	});
	
	// previous button
	$('#GridPrev').click( function() {
		
		currentGridIndex.prev('li').children('a.gridThumb').trigger('click');

		return false;
	});


	// apply button styles
	jQuery('.gridBtn').css({
		'-moz-border-radius': '3px',
		'-webkit-border-radius': '3px',
		'border-radius': '3px'
	});


});